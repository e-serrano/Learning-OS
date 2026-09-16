from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import ExerciseAttempt
from app.persistence.models import ExerciseAttemptModel
from app.persistence.repositories._util import dt_to_str, str_to_dt


def _to_model(attempt: ExerciseAttempt) -> ExerciseAttemptModel:
    return ExerciseAttemptModel(
        id=attempt.id,
        exercise_id=attempt.exercise_id,
        session_id=attempt.session_id,
        answer=attempt.answer,
        confidence=attempt.confidence,
        submitted_at=dt_to_str(attempt.submitted_at),
    )


def _to_entity(model: ExerciseAttemptModel) -> ExerciseAttempt:
    return ExerciseAttempt(
        id=model.id,
        exercise_id=model.exercise_id,
        session_id=model.session_id,
        answer=model.answer,
        confidence=model.confidence,  # type: ignore[arg-type]
        submitted_at=str_to_dt(model.submitted_at),  # type: ignore[arg-type]
    )


class SqlExerciseAttemptRepository:
    """Implements app.domain.ports.ExerciseAttemptRepository against
    exercise_attempts (T033 table, T072 port/adapter).

    `evaluation_id` on the domain entity has no matching column here --
    the schema's FK runs the other way (evaluations.attempt_id), so it
    always reads back as None; see docs/TASKS.md T072 note.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, attempt: ExerciseAttempt) -> None:
        with DbSession(self._engine) as db:
            db.add(_to_model(attempt))
            db.commit()

    def get(self, attempt_id: str) -> ExerciseAttempt | None:
        with DbSession(self._engine) as db:
            model = db.get(ExerciseAttemptModel, attempt_id)
            return _to_entity(model) if model is not None else None
