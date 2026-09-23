"""Full assessment-answer pipeline (fix on top of docs/TASKS.md T105).

Gap closed here: `AssessmentCompletionService.complete_assessment` (T090)
persists scored Evidence but never calls `MasteryUpdateService`/
`ReviewCreationService` afterward, so `Concept.mastery`/`.status` and the
next scheduled review stay stale after an assessment -- same shape of
gap T088's note flagged for reviews ("MasteryEngine already reads
Concept.retention... but nothing wrote it until now"), closed for
reviews by T104's `ReviewFlowService` and here for assessments the same
way T103's `AnswerFlowService` does it for regular exercises: update
mastery, then schedule the next review, once per concept the evidence
touched.

Also marks the scaffolding Activity `completed` -- `AssessmentCompletionService`
has no `ActivityRepository` dependency and never touches Activity status
(same split T103's `AnswerFlowService` makes for regular sessions), so
that responsibility lives here instead of in the API route, keeping
persistence access inside the service layer (docs/AGENTS.md layering).
"""

from dataclasses import dataclass

from app.domain.entities import Activity, Concept
from app.domain.enums import ActivityStatus
from app.domain.ports import ActivityRepository
from app.services.assessment_completion_service import (
    AssessmentCompletionResult,
    AssessmentCompletionService,
)
from app.services.mastery_update_service import MasteryUpdateService
from app.services.review_creation_service import ReviewCreationService

__all__ = ["AssessmentFlowResult", "AssessmentFlowService"]


@dataclass(frozen=True)
class AssessmentFlowResult:
    completion: AssessmentCompletionResult
    activity: Activity
    concepts: list[Concept]


class AssessmentFlowService:
    def __init__(
        self,
        activities: ActivityRepository,
        completion: AssessmentCompletionService,
        mastery_update: MasteryUpdateService,
        review_creation: ReviewCreationService,
    ) -> None:
        self._activities = activities
        self._completion = completion
        self._mastery_update = mastery_update
        self._review_creation = review_creation

    async def complete_assessment(
        self,
        exercise_id: str,
        session_id: str,
        activity_id: str,
        goal_id: str,
        answer: str,
        confidence: float,
    ) -> AssessmentFlowResult:
        result = await self._completion.complete_assessment(
            exercise_id, session_id, activity_id, answer, confidence
        )

        concept_ids = list(dict.fromkeys(e.concept_id for e in result.evidence))
        concepts: list[Concept] = []
        for concept_id in concept_ids:
            concepts.append(await self._mastery_update.update_mastery(concept_id, goal_id))
            self._review_creation.schedule_review(
                concept_id, goal_id, correctness=result.evaluation.correctness
            )

        activity = self._activities.get(activity_id)
        assert activity is not None
        completed = activity.model_copy(update={"status": ActivityStatus.COMPLETED})
        self._activities.update(completed)

        return AssessmentFlowResult(completion=result, activity=completed, concepts=concepts)
