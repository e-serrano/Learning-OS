from datetime import UTC, datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import ExerciseAttempt
from app.domain.ports import ExerciseAttemptRepository
from app.persistence.models import ExerciseModel
from app.persistence.repositories import SqlExerciseAttemptRepository

NOW = datetime.now(UTC)


def _accepts_port(port: ExerciseAttemptRepository) -> ExerciseAttemptRepository:
    return port


def _seed_exercise(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    with DbSession(engine) as db:
        db.add(
            ExerciseModel(
                id="exercise_1",
                type="sql",
                difficulty=2,
                goal_id=seeded["goal_id"],
                prompt="Write a query",
                solution="SELECT 1",
                metadata_json="{}",
                created_at=NOW.isoformat(),
            )
        )
        db.commit()


def _make_attempt(**overrides: object) -> ExerciseAttempt:
    defaults: dict[str, object] = dict(
        id="attempt_1",
        exercise_id="exercise_1",
        session_id="session_1",
        answer="SELECT 1;",
        confidence=72,
        submitted_at=NOW,
    )
    defaults.update(overrides)
    return ExerciseAttempt(**defaults)  # type: ignore[arg-type]


def test_satisfies_exercise_attempt_repository_port(engine: Engine) -> None:
    _accepts_port(SqlExerciseAttemptRepository(engine))


def test_add_then_get_roundtrips(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    _seed_exercise(engine, seeded)
    repo = SqlExerciseAttemptRepository(engine)
    attempt = _make_attempt()
    repo.add(attempt)

    assert repo.get("attempt_1") == attempt


def test_get_missing_returns_none(engine: Engine) -> None:
    assert SqlExerciseAttemptRepository(engine).get("missing") is None
