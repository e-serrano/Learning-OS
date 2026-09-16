from datetime import UTC, datetime

import pytest

from app.domain.entities import Activity, Session
from app.domain.enums import ActivityStatus, ActivityType, SessionMode, SessionStatus
from app.services.activity_selector import ActivityCandidate
from app.services.adaptive_activity_service import AdaptiveActivityService
from app.services.next_activity_service import (
    InactiveSessionError,
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
    return ActivityCandidate(concept_id=concept_id, score=score, breakdown={"importance": score})


def _service(
    sessions: list[Session] | None = None,
    ranked: list[ActivityCandidate] | None = None,
) -> AdaptiveActivityService:
    return AdaptiveActivityService(
        FakeSessionRepository(sessions if sessions is not None else [_session()]),
        FakeActivityRepository(),
        FakeActivitySelector(ranked if ranked is not None else [_candidate("concept_1")]),
        FakeIdGenerator(),
    )


def test_select_next_without_just_completed_picks_the_top_candidate() -> None:
    service = _service(ranked=[_candidate("concept_high", 5.0), _candidate("concept_low", 1.0)])

    result = service.select_next("session_1")

    assert result.activity.concept_ids == ["concept_high"]
    assert result.reason.concept_id == "concept_high"


def test_select_next_returns_the_explainable_reason_alongside_the_activity() -> None:
    candidate = _candidate("concept_1", 3.0)
    service = _service(ranked=[candidate])

    result = service.select_next("session_1")

    assert result.reason == candidate
    assert result.reason.breakdown  # explainable, not an opaque score


def test_select_next_skips_the_just_completed_concept_when_an_alternative_exists() -> None:
    service = _service(
        ranked=[_candidate("concept_just_done", 5.0), _candidate("concept_other", 1.0)]
    )

    result = service.select_next("session_1", just_completed_concept_id="concept_just_done")

    assert result.activity.concept_ids == ["concept_other"]


def test_select_next_falls_back_to_the_just_completed_concept_if_it_is_the_only_one() -> None:
    service = _service(ranked=[_candidate("concept_only", 5.0)])

    result = service.select_next("session_1", just_completed_concept_id="concept_only")

    assert result.activity.concept_ids == ["concept_only"]


def test_select_next_persists_an_active_exercise_activity() -> None:
    service = _service()

    result = service.select_next("session_1")

    assert result.activity.status == ActivityStatus.ACTIVE
    assert result.activity.type == ActivityType.EXERCISE


def test_select_next_raises_when_session_not_found() -> None:
    service = _service(sessions=[])

    with pytest.raises(SessionNotFoundError):
        service.select_next("missing_session")


def test_select_next_raises_when_session_not_active() -> None:
    service = _service(sessions=[_session(status=SessionStatus.COMPLETED)])

    with pytest.raises(InactiveSessionError):
        service.select_next("session_1")


def test_select_next_raises_when_no_candidates() -> None:
    service = _service(ranked=[])

    with pytest.raises(NoActivityCandidatesError):
        service.select_next("session_1")
