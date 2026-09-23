"""Full project-task-submission pipeline (docs/TASKS.md T106,
docs/API_SPEC.md #9: `POST /projects/{project_id}/tasks/{task_id}/submit`,
no documented request/response).

API_SPEC.md #9 has a single `submit` route, not a separate
submit-then-evaluate pair -- so this composes T094
(`ProjectSubmissionService.submit_task`, unscored Evidence) and T095
(`ProjectEvaluationService.evaluate_submission`, scored Evidence) into
the one HTTP action a client actually gets, unlike T090/T105's
assessments, which the spec gives two routes (`/answer` then
`/complete`).

Neither T094 nor T095 calls `MasteryUpdateService`/`ReviewCreationService`
after writing evidence -- same shape of gap closed for exercises by
T103's `AnswerFlowService`, for reviews by T104's `ReviewFlowService`,
and for assessments by the T105 follow-up fix (`AssessmentFlowService`)
-- closed here the same way, once per concept the scored evidence
touched. All concepts share one evaluation, so `correctness` for
`schedule_review` is read off any one of the scored Evidence rows.
"""

from dataclasses import dataclass

from app.domain.entities import Activity, Concept, Evidence
from app.services.mastery_update_service import MasteryUpdateService
from app.services.project_evaluation_service import ProjectEvaluationService
from app.services.project_submission_service import ProjectSubmissionService
from app.services.review_creation_service import ReviewCreationService

__all__ = ["ProjectFlowService", "ProjectSubmissionFlowResult"]


@dataclass(frozen=True)
class ProjectSubmissionFlowResult:
    task: Activity
    submission_evidence: list[Evidence]
    evaluation_evidence: list[Evidence]
    concepts: list[Concept]


class ProjectFlowService:
    def __init__(
        self,
        submission: ProjectSubmissionService,
        evaluation: ProjectEvaluationService,
        mastery_update: MasteryUpdateService,
        review_creation: ReviewCreationService,
    ) -> None:
        self._submission = submission
        self._evaluation = evaluation
        self._mastery_update = mastery_update
        self._review_creation = review_creation

    async def submit_task(
        self, project_id: str, task_id: str, goal_id: str, deliverable: str
    ) -> ProjectSubmissionFlowResult:
        submission = self._submission.submit_task(project_id, task_id, deliverable)
        evaluation_evidence = await self._evaluation.evaluate_submission(
            project_id, task_id, submission.task.session_id, deliverable
        )

        concept_ids = list(dict.fromkeys(e.concept_id for e in evaluation_evidence))
        correctness = next(
            (e.correctness for e in evaluation_evidence if e.correctness is not None), None
        )
        concepts: list[Concept] = []
        for concept_id in concept_ids:
            concepts.append(await self._mastery_update.update_mastery(concept_id, goal_id))
            if correctness is not None:
                self._review_creation.schedule_review(concept_id, goal_id, correctness=correctness)

        return ProjectSubmissionFlowResult(
            task=submission.task,
            submission_evidence=submission.evidence,
            evaluation_evidence=evaluation_evidence,
            concepts=concepts,
        )
