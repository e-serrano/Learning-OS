from datetime import UTC, datetime

import pytest

from app.domain.entities import LearningGoal
from app.domain.enums import GoalStatus, TargetLevel
from app.services.goal_service import GoalApplicationService, InvalidGoalError

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeGoalRepository:
    def __init__(self) -> None:
        self.added: list[LearningGoal] = []

    def add(self, goal: LearningGoal) -> None:
        self.added.append(goal)

    def get(self, goal_id: str) -> LearningGoal | None:
        return next((g for g in self.added if g.id == goal_id), None)

    def list_all(self) -> list[LearningGoal]:
        return list(self.added)

    def update(self, goal: LearningGoal) -> None:
        raise NotImplementedError


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


def _service(
    repo: FakeGoalRepository | None = None,
) -> tuple[GoalApplicationService, FakeGoalRepository]:
    goals = repo or FakeGoalRepository()
    return GoalApplicationService(goals, FakeClock(NOW), FakeIdGenerator()), goals


def test_create_goal_persists_and_returns_it_as_draft() -> None:
    service, goals = _service()

    goal = service.create_goal(title="Learn BigQuery", target_level=TargetLevel.PROFESSIONAL)

    assert goal.status == GoalStatus.DRAFT
    assert goals.added == [goal]


def test_create_goal_assigns_a_generated_id_and_matching_timestamps() -> None:
    service, _ = _service()

    goal = service.create_goal(title="Learn BigQuery", target_level=TargetLevel.PROFESSIONAL)

    assert goal.id == "goal_1"
    assert goal.created_at == NOW
    assert goal.updated_at == NOW


def test_create_goal_defaults_optional_fields() -> None:
    service, _ = _service()

    goal = service.create_goal(title="Learn BigQuery", target_level=TargetLevel.PROFESSIONAL)

    assert goal.description is None
    assert goal.domain is None
    assert goal.deadline is None
    assert goal.available_minutes_per_week is None
    assert goal.priority == 3


def test_create_goal_passes_through_provided_optional_fields() -> None:
    service, _ = _service()
    deadline = datetime(2026, 6, 1, tzinfo=UTC)

    goal = service.create_goal(
        title="Learn BigQuery",
        target_level=TargetLevel.PROFESSIONAL,
        description="Get to production-ready SQL",
        domain="data-engineering",
        priority=5,
        deadline=deadline,
        available_minutes_per_week=180,
    )

    assert goal.description == "Get to production-ready SQL"
    assert goal.domain == "data-engineering"
    assert goal.priority == 5
    assert goal.deadline == deadline
    assert goal.available_minutes_per_week == 180


def test_blank_title_is_rejected_without_persisting() -> None:
    service, goals = _service()

    with pytest.raises(InvalidGoalError):
        service.create_goal(title="   ", target_level=TargetLevel.BEGINNER)

    assert goals.added == []


def test_goal_application_service_has_no_vault_dependency() -> None:
    """Creating a goal must never touch the vault automatically
    (docs/AGENTS.md #3) -- enforced architecturally by never accepting a
    VaultPort at all, not just by convention."""
    import inspect

    params = inspect.signature(GoalApplicationService.__init__).parameters
    assert "vault" not in params
