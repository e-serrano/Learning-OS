from datetime import UTC, datetime

from sqlalchemy import Engine

from app.domain.entities import LearningGoal
from app.domain.enums import GoalStatus, TargetLevel
from app.domain.ports import GoalRepository
from app.persistence.repositories import SqlGoalRepository

NOW = datetime.now(UTC)


def _accepts_port(port: GoalRepository) -> GoalRepository:
    """mypy-checked: SqlGoalRepository must satisfy the GoalRepository port."""
    return port


def _make_goal(**overrides: object) -> LearningGoal:
    defaults: dict[str, object] = dict(
        id="goal_1",
        title="Learn BigQuery",
        target_level=TargetLevel.PROFESSIONAL,
        status=GoalStatus.DRAFT,
        priority=3,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return LearningGoal(**defaults)  # type: ignore[arg-type]


def test_satisfies_goal_repository_port(engine: Engine) -> None:
    _accepts_port(SqlGoalRepository(engine))


def test_add_then_get_roundtrips(engine: Engine) -> None:
    repo = SqlGoalRepository(engine)
    goal = _make_goal()
    repo.add(goal)

    loaded = repo.get("goal_1")
    assert loaded == goal


def test_get_missing_returns_none(engine: Engine) -> None:
    repo = SqlGoalRepository(engine)
    assert repo.get("does-not-exist") is None


def test_list_all_returns_every_goal(engine: Engine) -> None:
    repo = SqlGoalRepository(engine)
    repo.add(_make_goal(id="goal_1"))
    repo.add(_make_goal(id="goal_2", title="Learn dbt"))

    goals = {g.id for g in repo.list_all()}
    assert goals == {"goal_1", "goal_2"}


def test_update_persists_changes(engine: Engine) -> None:
    repo = SqlGoalRepository(engine)
    repo.add(_make_goal())

    updated = _make_goal(status=GoalStatus.ACTIVE)
    repo.update(updated)

    assert repo.get("goal_1").status == GoalStatus.ACTIVE  # type: ignore[union-attr]


def test_optional_fields_roundtrip_as_none(engine: Engine) -> None:
    repo = SqlGoalRepository(engine)
    repo.add(_make_goal())

    loaded = repo.get("goal_1")
    assert loaded is not None
    assert loaded.description is None
    assert loaded.deadline is None
