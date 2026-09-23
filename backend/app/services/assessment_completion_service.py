"""Assessment completion -- answers and grades a transfer assessment,
explicitly surfacing whether transfer and independence were
demonstrated (docs/TASKS.md T090).

A transfer scenario is a regular Exercise (T089 persists it the same
way as any other), so grading it needs no new scoring logic -- this
chains the exact same pipeline a regular exercise already uses
(AnswerSubmissionService T072 -> EvaluatorService T073 ->
EvidenceCreationService T074). What T090 adds is turning the raw
`transfer`/`independence` scores (docs/AI_CONTRACTS.md #8, already
computed for every evaluation, not transfer-specific) into an explicit,
thresholded, measurable pass/fail judgment on those two dimensions --
docs/TASKS.md T091 explicitly wants "a later *measurable* transfer",
not scores buried inside an Evaluation record.

Exercise has no field marking "this is a transfer assessment" (T089
persists it as a plain Exercise), so EvidenceCreationService cannot
infer `source_type` from the exercise alone -- this service passes
`EvidenceSourceType.ASSESSMENT` explicitly into `create_evidence`
rather than letting it fall back to the default `EXERCISE` a regular
exercise flow (AnswerFlowService) relies on.
"""

from dataclasses import dataclass

from app.domain.entities import Evaluation, Evidence, ExerciseAttempt
from app.domain.enums import EvidenceSourceType
from app.services.answer_submission_service import AnswerSubmissionService
from app.services.evaluator_service import EvaluatorService
from app.services.evidence_creation_service import EvidenceCreationService

TRANSFER_SUCCESS_THRESHOLD = 0.6
"""Matches the same 0.6 "successful recall" threshold ReviewScheduler
(T063) already uses -- one consistent bar for "good enough" across the
codebase rather than a second, arbitrary number."""

INDEPENDENCE_SUCCESS_THRESHOLD = 0.6


@dataclass(frozen=True)
class AssessmentCompletionResult:
    attempt: ExerciseAttempt
    evaluation: Evaluation
    evidence: list[Evidence]
    transfer_demonstrated: bool
    independence_demonstrated: bool


class AssessmentCompletionService:
    def __init__(
        self,
        answer_submission: AnswerSubmissionService,
        evaluator: EvaluatorService,
        evidence_creation: EvidenceCreationService,
    ) -> None:
        self._answer_submission = answer_submission
        self._evaluator = evaluator
        self._evidence_creation = evidence_creation

    async def complete_assessment(
        self,
        exercise_id: str,
        session_id: str,
        activity_id: str,
        answer: str,
        confidence: float,
    ) -> AssessmentCompletionResult:
        attempt = self._answer_submission.submit_answer(exercise_id, session_id, answer, confidence)
        evaluation = await self._evaluator.evaluate(attempt.id)
        evidence = self._evidence_creation.create_evidence(
            evaluation.id, activity_id, source_type=EvidenceSourceType.ASSESSMENT
        )

        return AssessmentCompletionResult(
            attempt=attempt,
            evaluation=evaluation,
            evidence=evidence,
            transfer_demonstrated=evaluation.transfer >= TRANSFER_SUCCESS_THRESHOLD,
            independence_demonstrated=evaluation.independence >= INDEPENDENCE_SUCCESS_THRESHOLD,
        )
