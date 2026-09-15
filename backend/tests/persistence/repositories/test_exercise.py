from datetime import UTC, datetime

from sqlalchemy import Engine

from app.domain.entities import Exercise
from app.domain.enums import ExerciseType
from app.domain.ports import ExerciseRepository
from app.persistence.repositories import SqlExerciseRepository

NOW = datetime.now(UTC)


def _accepts_port(port: ExerciseRepository) -> ExerciseRepository:
    return port


def _make_exercise(seeded: dict, **overrides: object) -> Exercise:  # type: ignore[type-arg]
    defaults: dict[str, object] = dict(
        id="exercise_1",
        type=ExerciseType.SQL,
        difficulty=3,
        goal_id=seeded["goal_id"],
        concept_ids=[seeded["concept_id"]],
        prompt="Write a query using ROW_NUMBER()",
        solution="SELECT ROW_NUMBER() OVER (...) FROM t",
        hints=["Think about partitioning", "Use ORDER BY"],
        common_mistakes=["Forgetting PARTITION BY"],
        transfer_variant="Now do it with RANK()",
        created_at=NOW,
    )
    defaults.update(overrides)
    return Exercise(**defaults)  # type: ignore[arg-type]


def test_satisfies_exercise_repository_port(engine: Engine) -> None:
    _accepts_port(SqlExerciseRepository(engine))


def test_add_then_get_roundtrips(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlExerciseRepository(engine)
    exercise = _make_exercise(seeded)
    repo.add(exercise)

    assert repo.get("exercise_1") == exercise


def test_concept_ids_come_from_join_table(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlExerciseRepository(engine)
    repo.add(_make_exercise(seeded, concept_ids=[seeded["concept_id"]]))

    loaded = repo.get("exercise_1")
    assert loaded is not None
    assert loaded.concept_ids == [seeded["concept_id"]]


def test_hints_and_common_mistakes_roundtrip_via_metadata(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlExerciseRepository(engine)
    repo.add(_make_exercise(seeded, concept_ids=[]))

    loaded = repo.get("exercise_1")
    assert loaded is not None
    assert loaded.hints == ["Think about partitioning", "Use ORDER BY"]
    assert loaded.common_mistakes == ["Forgetting PARTITION BY"]
    assert loaded.transfer_variant == "Now do it with RANK()"


def test_get_missing_returns_none(engine: Engine) -> None:
    repo = SqlExerciseRepository(engine)
    assert repo.get("does-not-exist") is None
