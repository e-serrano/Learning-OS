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

`source_type` has two ways of being decided, in priority order:

1. The caller passes it explicitly (docs/TASKS.md T090 fix) -- e.g.
   `AssessmentCompletionService` always passes
   `EvidenceSourceType.ASSESSMENT`, since nothing about a transfer
   assessment's own `Exercise` distinguishes it from an ordinary one.
2. Otherwise (`source_type=None`, the default -- `AnswerFlowService`'s
   ordinary answer route never passes one), it's inferred from the
   underlying Exercise's own `type`: `TEACH_BACK` if
   `exercise.type == ExerciseType.TEACH_BACK`, `EXERCISE` otherwise
   (docs/TASKS.md T133).

Both previously hardcoded to `EXERCISE` unconditionally, leaving
`EvidenceSourceType.ASSESSMENT`/`TEACH_BACK` reserved in the enum
(docs/DOMAIN_MODEL.md #6) but dead code. `None` (not
`EvidenceSourceType.EXERCISE`) is the sentinel specifically so these two
independent fixes compose instead of one silently overriding the other
-- a real default of `EXERCISE` would have made every caller's own
choice indistinguishable from "caller didn't specify," and the
type-inference branch would have clobbered `AssessmentCompletionService`'s
explicit `ASSESSMENT` on every call.
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
        source_type: EvidenceSourceType | None = None,
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

        if source_type is None:
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
