"""Mistake update -- creates/increments Mistakes from a valid
Evaluation's reported misconceptions (docs/TASKS.md T076).

Same chain-traversal need as T074 (Evidence creation): Evaluation only
carries `attempt_id`, so concept_id(s)/goal_id come from
Evaluation -> ExerciseAttempt -> Exercise. When an exercise targets
multiple concepts, each reported misconception is recorded against
every targeted concept -- EvaluatorResponse.misconceptions has no
per-item concept mapping to disambiguate further.
"""

from app.domain.entities import Mistake
from app.domain.ports import EvaluationRepository, ExerciseAttemptRepository, ExerciseRepository
from app.services.answer_submission_service import ExerciseNotFoundError
from app.services.evaluator_service import AttemptNotFoundError
from app.services.evidence_creation_service import EvaluationNotFoundError
from app.services.mistake_tracker import MistakeTracker


class MistakeUpdateService:
    def __init__(
        self,
        evaluations: EvaluationRepository,
        attempts: ExerciseAttemptRepository,
        exercises: ExerciseRepository,
        mistake_tracker: MistakeTracker,
    ) -> None:
        self._evaluations = evaluations
        self._attempts = attempts
        self._exercises = exercises
        self._mistake_tracker = mistake_tracker

    def record_from_evaluation(self, evaluation_id: str) -> list[Mistake]:
        evaluation = self._evaluations.get(evaluation_id)
        if evaluation is None:
            raise EvaluationNotFoundError(evaluation_id)
        if not evaluation.misconceptions:
            return []

        attempt = self._attempts.get(evaluation.attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(evaluation.attempt_id)
        exercise = self._exercises.get(attempt.exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError(attempt.exercise_id)

        recorded: list[Mistake] = []
        for concept_id in exercise.concept_ids:
            for description in evaluation.misconceptions:
                recorded.append(
                    self._mistake_tracker.record(concept_id, exercise.goal_id, description)
                )
        return recorded
