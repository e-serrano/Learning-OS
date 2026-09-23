"""Full submit-answer pipeline (docs/TASKS.md T103, docs/API_SPEC.md
#6: `POST /sessions/{id}/activities/{id}/answer`), composing T072-T078
into the single HTTP action the spec describes:

    AnswerSubmissionService.submit_answer   (T072)
    -> EvaluatorService.evaluate            (T073, async AI call)
    -> EvidenceCreationService.create_evidence   (T074)
    -> MistakeUpdateService.record_from_evaluation   (T076)
    -> per concept touched: MasteryUpdateService.update_mastery   (T075)
                             ReviewCreationService.schedule_review   (T077)
    -> AdaptiveActivityService.select_next + ActivityContentService.attach_exercise
       for the embedded `next_activity` (T078/T103)

`"knowledge_updates"` has no shape anywhere in API_SPEC.md (only an
empty `[]` example) -- defined here as one entry per concept the
evidence touched, carrying exactly what a client needs to reflect the
update without a second round-trip: the concept's new mastery/status,
how many mistakes this answer added, and when it's next due for review.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.entities import Evaluation
from app.domain.enums import ActivityStatus, ConceptStatus
from app.domain.ports import ActivityRepository, SessionRepository
from app.domain.value_objects import ConfidencePercent
from app.services.activity_content_service import ActivityContent, ActivityContentService
from app.services.adaptive_activity_service import AdaptiveActivityService
from app.services.answer_submission_service import AnswerSubmissionService
from app.services.evaluator_service import EvaluatorService
from app.services.evidence_creation_service import EvidenceCreationService
from app.services.mastery_update_service import MasteryUpdateService
from app.services.mistake_update_service import MistakeUpdateService
from app.services.next_activity_service import NoActivityCandidatesError, SessionNotFoundError
from app.services.review_creation_service import ReviewCreationService


class ActivityNotFoundError(Exception):
    pass


class ActivityHasNoExerciseError(Exception):
    pass


@dataclass(frozen=True)
class KnowledgeUpdate:
    concept_id: str
    mastery: float
    status: ConceptStatus
    mistakes_recorded: int
    next_review_scheduled_at: datetime


@dataclass(frozen=True)
class AnswerResult:
    evaluation: Evaluation
    knowledge_updates: list[KnowledgeUpdate]
    next_activity: ActivityContent | None


class AnswerFlowService:
    def __init__(
        self,
        sessions: SessionRepository,
        activities: ActivityRepository,
        answer_submission: AnswerSubmissionService,
        evaluator: EvaluatorService,
        evidence_creation: EvidenceCreationService,
        mistake_update: MistakeUpdateService,
        mastery_update: MasteryUpdateService,
        review_creation: ReviewCreationService,
        adaptive_activity: AdaptiveActivityService,
        activity_content: ActivityContentService,
    ) -> None:
        self._sessions = sessions
        self._activities = activities
        self._answer_submission = answer_submission
        self._evaluator = evaluator
        self._evidence_creation = evidence_creation
        self._mistake_update = mistake_update
        self._mastery_update = mastery_update
        self._review_creation = review_creation
        self._adaptive_activity = adaptive_activity
        self._activity_content = activity_content

    async def submit_answer(
        self, session_id: str, activity_id: str, answer: str, confidence: ConfidencePercent
    ) -> AnswerResult:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)

        activity = self._activities.get(activity_id)
        if activity is None or activity.session_id != session_id:
            raise ActivityNotFoundError(activity_id)
        if activity.exercise_id is None:
            raise ActivityHasNoExerciseError(activity_id)

        attempt = self._answer_submission.submit_answer(
            activity.exercise_id, session_id, answer, confidence
        )
        evaluation = await self._evaluator.evaluate(attempt.id)

        evidence = self._evidence_creation.create_evidence(evaluation.id, activity_id)
        mistakes = self._mistake_update.record_from_evaluation(evaluation.id)

        concept_ids = list(dict.fromkeys(e.concept_id for e in evidence))
        knowledge_updates: list[KnowledgeUpdate] = []
        for concept_id in concept_ids:
            concept = await self._mastery_update.update_mastery(concept_id, session.goal_id)
            review = self._review_creation.schedule_review(
                concept_id, session.goal_id, correctness=evaluation.correctness
            )
            concept_mistakes = [m for m in mistakes if m.concept_id == concept_id]
            knowledge_updates.append(
                KnowledgeUpdate(
                    concept_id=concept_id,
                    mastery=concept.mastery,
                    status=concept.status,
                    mistakes_recorded=len(concept_mistakes),
                    next_review_scheduled_at=review.scheduled_at,
                )
            )

        self._activities.update(activity.model_copy(update={"status": ActivityStatus.COMPLETED}))

        next_activity: ActivityContent | None = None
        try:
            picked = self._adaptive_activity.select_next(
                session_id, just_completed_concept_id=concept_ids[0] if concept_ids else None
            )
            next_activity = await self._activity_content.attach_exercise(
                session.goal_id, picked.activity
            )
        except NoActivityCandidatesError:
            next_activity = None

        return AnswerResult(
            evaluation=evaluation,
            knowledge_updates=knowledge_updates,
            next_activity=next_activity,
        )
