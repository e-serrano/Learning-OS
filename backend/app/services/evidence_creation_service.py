"""Evidence creation -- converts a valid Evaluation into immutable
Evidence (docs/TASKS.md T074).

An Exercise can target multiple concepts (`concept_ids`), but Evidence
carries exactly one `concept_id` (docs/DOMAIN_MODEL.md #6) -- this
service fans out one Evidence row per concept the exercise targeted.

`activity_id` is not derivable from the evaluation/attempt/exercise
chain -- neither ExerciseAttempt nor Exercise records which Activity an
answer was submitted for (docs/DATABASE_SCHEMA.md's exercise_attempts
has no such column). It is caller-supplied context, the same way
docs/API_SPEC.md's answer endpoint carries `activity_id` in its own URL
path (`/sessions/{session_id}/activities/{activity_id}/answer`) rather
than on the attempt itself.

`source_type` is `EvidenceSourceType.TEACH_BACK` when the underlying
Exercise's own `type` is `ExerciseType.TEACH_BACK`, `EXERCISE` otherwise
(docs/TASKS.md T133) -- previously always hardcoded to `EXERCISE`
regardless of exercise type, leaving `EvidenceSourceType.TEACH_BACK`
reserved in the enum (docs/DOMAIN_MODEL.md #6) but dead code. Answering a
teach-back exercise goes through this exact same route/service
unchanged (docs/TASKS.md T133 needed no new answer/evaluation pipeline,
only this one type-aware branch plus a way to generate a teach-back
Exercise in the first place, see `teach_back_service.py`).
"""

from app.domain.entities import Evidence
from app.domain.enums import EvidenceSourceType, ExerciseType
from app.domain.ports import (
    ClockPort,
    EvaluationRepository,
    EvidenceRepository,
    ExerciseAttemptRepository,
    ExerciseRepository,
    IdGeneratorPort,
)
from app.services.answer_submission_service import ExerciseNotFoundError
from app.services.evaluator_service import AttemptNotFoundError


class EvaluationNotFoundError(Exception):
    pass


class EvidenceCreationService:
    def __init__(
        self,
        evaluations: EvaluationRepository,
        attempts: ExerciseAttemptRepository,
        exercises: ExerciseRepository,
        evidence: EvidenceRepository,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._evaluations = evaluations
        self._attempts = attempts
        self._exercises = exercises
        self._evidence = evidence
        self._clock = clock
        self._ids = ids

    def create_evidence(
        self,
        evaluation_id: str,
        activity_id: str,
        source_type: EvidenceSourceType = EvidenceSourceType.EXERCISE,
    ) -> list[Evidence]:
        evaluation = self._evaluations.get(evaluation_id)
        if evaluation is None:
            raise EvaluationNotFoundError(evaluation_id)
        attempt = self._attempts.get(evaluation.attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(evaluation.attempt_id)
        exercise = self._exercises.get(attempt.exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError(attempt.exercise_id)

        source_type = (
            EvidenceSourceType.TEACH_BACK
            if exercise.type == ExerciseType.TEACH_BACK
            else EvidenceSourceType.EXERCISE
        )

        now = self._clock.now()
        created: list[Evidence] = []
        for concept_id in exercise.concept_ids:
            record = Evidence(
                id=self._ids.new_id("evidence"),
                concept_id=concept_id,
                goal_id=exercise.goal_id,
                session_id=attempt.session_id,
                activity_id=activity_id,
                source_type=source_type,
                difficulty=exercise.difficulty,
                correctness=evaluation.correctness,
                reasoning=evaluation.reasoning,
                independence=evaluation.independence,
                transfer=evaluation.transfer,
                confidence=attempt.confidence / 100,
                timestamp=now,
                metadata={"evaluation_id": evaluation_id, "attempt_id": attempt.id},
            )
            self._evidence.add(record)
            created.append(record)
        return created
