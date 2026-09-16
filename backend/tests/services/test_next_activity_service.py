from datetime import UTC, datetime

import pytest

from app.domain.entities import Activity, Session
from app.domain.enums import ActivityStatus, ActivityType, SessionMode, SessionStatus
from app.services.activity_selector import ActivityCandidate
from app.services.next_activity_service import (
    InactiveSessionError,
    NextActivityService,
    NoActivityCandidatesError,
    SessionNotFoundError,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeSessionRepository:
    def __init__(self, sessions: list[Session]) -> None:
        self._by_id = {s.id: s for s in sessions}

    def get(self, session_id: str) -> Session | None:
        return self._by_id.get(session_id)

    def add(self, session: Session) -> None:
        self._by_id[session.id] = session

    def update(self, session: Session) -> None:
        self._by_id[session.id] = session


class FakeActivityRepository:
    def __init__(self, activities: list[Activity] | None = None) -> None:
        self._activities = list(activities or [])

    def add(self, activity: Activity) -> None:
        self._activities.append(activity)

    def get(self, activity_id: str) -> Activity | None:
        return next((a for a in self._activities if a.id == activity_id), None)

    def list_by_session(self, session_id: str) -> list[Activity]:
        return [a for a in self._activities if a.session_id == session_id]

    def update(self, activity: Activity) -> None:
        raise NotImplementedError


class FakeActivitySelector:
    def __init__(self, ranked: list[ActivityCandidate]) -> None:
        self._ranked = ranked

    def rank(self, goal_id: str) -> list[ActivityCandidate]:
        return self._ranked


class FakeIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


def _session(**overrides: object) -> Session:
    defaults: dict[str, object] = dict(
        id="session_1",
        goal_id="goal_1",
        mode=SessionMode.GUIDED,
        objective="Practice",
        status=SessionStatus.ACTIVE,
        started_at=NOW,
    )
    defaults.update(overrides)
    return Session(**defaults)  # type: ignore[arg-type]


def _candidate(concept_id: str, score: float = 1.0) -> ActivityCandidate:
    return ActivityCandidate(concept_id=concept_id, score=score, breakdown={})


def _service(
    sessions: list[Session] | None = None,
    activities: list[Activity] | None = None,
    ranked: list[ActivityCandidate] | None = None,
) -> tuple[NextActivityService, FakeActivityRepository]:
    activity_repo = FakeActivityRepository(activities)
    service = NextActivityService(
        FakeSessionRepository(sessions if sessions is not None else [_session()]),
        activity_repo,
        FakeActivitySelector(ranked if ranked is not None else [_candidate("concept_1")]),
        FakeIdGenerator(),
    )
    return service, activity_repo


def test_select_next_creates_and_persists_an_active_exercise_activity() -> None:
    service, activities = _service()

    activity = service.select_next("session_1")

    assert activity.session_id == "session_1"
    assert activity.type == ActivityType.EXERCISE
    assert activity.status == ActivityStatus.ACTIVE
    assert activity.concept_ids == ["concept_1"]
    assert activities.get(activity.id) == activity


def test_select_next_picks_the_top_ranked_candidate() -> None:
    service, _ = _service(ranked=[_candidate("concept_high", 5.0), _candidate("concept_low", 1.0)])

    activity = service.select_next("session_1")

    assert activity.concept_ids == ["concept_high"]


def test_select_next_raises_when_session_not_found() -> None:
    service, activities = _service(sessions=[])

    with pytest.raises(SessionNotFoundError):
        service.select_next("missing_session")

    assert activities.list_by_session("missing_session") == []


def test_select_next_raises_when_session_not_active() -> None:
    service, _ = _service(sessions=[_session(status=SessionStatus.COMPLETED)])

    with pytest.raises(InactiveSessionError):
        service.select_next("session_1")


def test_select_next_raises_when_no_candidates() -> None:
    service, _ = _service(ranked=[])

    with pytest.raises(NoActivityCandidatesError):
        service.select_next("session_1")


def test_select_next_increments_sequence_from_existing_activities() -> None:
    existing = Activity(
        id="activity_existing",
        session_id="session_1",
        type=ActivityType.EXERCISE,
        sequence=1,
        concept_ids=["concept_1"],
        status=ActivityStatus.COMPLETED,
    )
    service, _ = _service(activities=[existing])

    activity = service.select_next("session_1")

    assert activity.sequence == 2


def test_select_next_first_activity_gets_sequence_one() -> None:
    service, _ = _service()

    activity = service.select_next("session_1")

    assert activity.sequence == 1
