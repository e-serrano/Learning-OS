from datetime import UTC, datetime

import pytest

from app.domain.entities import Exercise, ExerciseAttempt, Session
from app.domain.enums import ExerciseType, SessionMode, SessionStatus
from app.services.answer_submission_service import (
    AnswerSubmissionService,
    ExerciseNotFoundError,
)
from app.services.next_activity_service import InactiveSessionError, SessionNotFoundError

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeExerciseRepository:
    def __init__(self, exercises: list[Exercise]) -> None:
        self._by_id = {e.id: e for e in exercises}

    def get(self, exercise_id: str) -> Exercise | None:
        return self._by_id.get(exercise_id)

    def add(self, exercise: Exercise) -> None:
        self._by_id[exercise.id] = exercise


class FakeSessionRepository:
    def __init__(self, sessions: list[Session]) -> None:
        self._by_id = {s.id: s for s in sessions}

    def get(self, session_id: str) -> Session | None:
        return self._by_id.get(session_id)

    def add(self, session: Session) -> None:
        self._by_id[session.id] = session

    def update(self, session: Session) -> None:
        self._by_id[session.id] = session


class FakeExerciseAttemptRepository:
    def __init__(self) -> None:
        self.added: list[ExerciseAttempt] = []

    def add(self, attempt: ExerciseAttempt) -> None:
        self.added.append(attempt)

    def get(self, attempt_id: str) -> ExerciseAttempt | None:
        return next((a for a in self.added if a.id == attempt_id), None)


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


def _exercise(**overrides: object) -> Exercise:
    defaults: dict[str, object] = dict(
        id="exercise_1",
        type=ExerciseType.SQL,
        difficulty=3,
        goal_id="goal_1",
        prompt="Write a query",
        solution="SELECT 1",
        created_at=NOW,
    )
    defaults.update(overrides)
    return Exercise(**defaults)  # type: ignore[arg-type]


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


def _service(
    exercises: list[Exercise] | None = None, sessions: list[Session] | None = None
) -> tuple[AnswerSubmissionService, FakeExerciseAttemptRepository]:
    attempts = FakeExerciseAttemptRepository()
    service = AnswerSubmissionService(
        FakeExerciseRepository(exercises if exercises is not None else [_exercise()]),
        FakeSessionRepository(sessions if sessions is not None else [_session()]),
        attempts,
        FakeClock(NOW),
        FakeIdGenerator(),
    )
    return service, attempts


def test_submit_answer_persists_answer_and_confidence() -> None:
    service, attempts = _service()

    attempt = service.submit_answer("exercise_1", "session_1", "SELECT 1;", confidence=72)

    assert attempt.answer == "SELECT 1;"
    assert attempt.confidence == 72
    assert attempt.exercise_id == "exercise_1"
    assert attempt.session_id == "session_1"
    assert attempt.submitted_at == NOW
    assert attempts.added == [attempt]


def test_submit_answer_assigns_generated_id() -> None:
    service, _ = _service()

    attempt = service.submit_answer("exercise_1", "session_1", "answer", confidence=50)

    assert attempt.id == "attempt_1"


def test_submit_answer_raises_when_exercise_not_found() -> None:
    service, attempts = _service(exercises=[])

    with pytest.raises(ExerciseNotFoundError):
        service.submit_answer("missing_exercise", "session_1", "answer", confidence=50)

    assert attempts.added == []


def test_submit_answer_raises_when_session_not_found() -> None:
    service, attempts = _service(sessions=[])

    with pytest.raises(SessionNotFoundError):
        service.submit_answer("exercise_1", "missing_session", "answer", confidence=50)

    assert attempts.added == []


def test_submit_answer_raises_when_session_not_active() -> None:
    service, attempts = _service(sessions=[_session(status=SessionStatus.COMPLETED)])

    with pytest.raises(InactiveSessionError):
        service.submit_answer("exercise_1", "session_1", "answer", confidence=50)

    assert attempts.added == []
