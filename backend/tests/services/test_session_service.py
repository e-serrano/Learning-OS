from datetime import UTC, datetime

import pytest

from app.domain.entities import LearningGoal, Session
from app.domain.enums import GoalStatus, SessionMode, SessionStatus, TargetLevel
from app.services.context_builder import GoalNotFoundError
from app.services.session_service import InvalidSessionError, SessionApplicationService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeGoalRepository:
    def __init__(self, goals: list[LearningGoal]) -> None:
        self._by_id = {g.id: g for g in goals}

    def get(self, goal_id: str) -> LearningGoal | None:
        return self._by_id.get(goal_id)

    def list_all(self) -> list[LearningGoal]:
        return list(self._by_id.values())

    def add(self, goal: LearningGoal) -> None:
        self._by_id[goal.id] = goal

    def update(self, goal: LearningGoal) -> None:
        self._by_id[goal.id] = goal


class FakeSessionRepository:
    def __init__(self) -> None:
        self.added: list[Session] = []

    def add(self, session: Session) -> None:
        self.added.append(session)

    def get(self, session_id: str) -> Session | None:
        return next((s for s in self.added if s.id == session_id), None)

    def update(self, session: Session) -> None:
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


def _goal(**overrides: object) -> LearningGoal:
    defaults: dict[str, object] = dict(
        id="goal_1",
        title="Learn SQL",
        target_level=TargetLevel.PROFESSIONAL,
        status=GoalStatus.ACTIVE,
        priority=3,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return LearningGoal(**defaults)  # type: ignore[arg-type]


def _service(
    goals: list[LearningGoal] | None = None,
) -> tuple[SessionApplicationService, FakeSessionRepository]:
    sessions = FakeSessionRepository()
    service = SessionApplicationService(
        FakeGoalRepository(goals or [_goal()]), sessions, FakeClock(NOW), FakeIdGenerator()
    )
    return service, sessions


def test_create_session_persists_active_session_started_now() -> None:
    service, sessions = _service()

    session = service.create_session("goal_1", SessionMode.GUIDED, duration_minutes=30)

    assert session.status == SessionStatus.ACTIVE
    assert session.started_at == NOW
    assert session.ended_at is None
    assert sessions.added == [session]


def test_create_session_assigns_generated_id_and_mode() -> None:
    service, _ = _service()

    session = service.create_session("goal_1", SessionMode.PRACTICE, duration_minutes=15)

    assert session.id == "session_1"
    assert session.mode == SessionMode.PRACTICE
    assert session.goal_id == "goal_1"


def test_create_session_defaults_objective_from_goal_title() -> None:
    service, _ = _service(goals=[_goal(title="Learn BigQuery")])

    session = service.create_session("goal_1", SessionMode.GUIDED, duration_minutes=30)

    assert "Learn BigQuery" in session.objective


def test_create_session_accepts_custom_objective() -> None:
    service, _ = _service()

    session = service.create_session(
        "goal_1", SessionMode.GUIDED, duration_minutes=30, objective="Master window functions"
    )

    assert session.objective == "Master window functions"


def test_create_session_raises_when_goal_not_found() -> None:
    service, sessions = _service(goals=[])

    with pytest.raises(GoalNotFoundError):
        service.create_session("missing_goal", SessionMode.GUIDED, duration_minutes=30)

    assert sessions.added == []


@pytest.mark.parametrize("duration_minutes", [0, -5])
def test_create_session_rejects_non_positive_duration(duration_minutes: int) -> None:
    service, sessions = _service()

    with pytest.raises(InvalidSessionError):
        service.create_session("goal_1", SessionMode.GUIDED, duration_minutes=duration_minutes)

    assert sessions.added == []
