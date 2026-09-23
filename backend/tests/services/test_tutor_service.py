from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import TutorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Concept, LearningGoal, Session
from app.domain.enums import ConceptStatus, GoalStatus, SessionMode, SessionStatus, TargetLevel
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import (
    SqlConceptRelationRepository,
    SqlConceptRepository,
    SqlEvidenceRepository,
    SqlGoalRepository,
    SqlMistakeRepository,
    SqlSessionRepository,
)
from app.services.context_builder import ContextBuilder, GoalNotFoundError
from app.services.next_activity_service import InactiveSessionError, SessionNotFoundError
from app.services.tutor_service import SessionNotSocraticError, TutorService, TutorTurn

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class NeverCalledProvider:
    async def generate(self, request: object, response_model: object) -> object:
        raise AssertionError("AI provider must not be called")


class FakeGoalRepository:
    """`sessions.goal_id` is FK-constrained against `goals.id` (docs/
    DATABASE_SCHEMA.md), so a session referencing a missing goal cannot be
    constructed through the real SQL repositories -- only used for the one
    test exercising that otherwise-unreachable-in-SQLite defensive path."""

    def __init__(self, goals: list[LearningGoal]) -> None:
        self._by_id = {g.id: g for g in goals}

    def get(self, goal_id: str) -> LearningGoal | None:
        return self._by_id.get(goal_id)


class FakeSessionRepository:
    def __init__(self, sessions: list[Session]) -> None:
        self._by_id = {s.id: s for s in sessions}

    def get(self, session_id: str) -> Session | None:
        return self._by_id.get(session_id)


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _seed_goal_and_concept(engine: Engine) -> None:
    SqlGoalRepository(engine).add(
        LearningGoal(
            id="goal_1",
            title="Learn SQL",
            target_level=TargetLevel.PROFESSIONAL,
            status=GoalStatus.ACTIVE,
            priority=3,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    SqlConceptRepository(engine).add(
        Concept(
            id="concept_1",
            title="Window Functions",
            domain="sql",
            status=ConceptStatus.LEARNING,
            mastery=1,
            confidence=20,
            importance=3,
            retention=10,
            created_at=NOW,
            updated_at=NOW,
        )
    )


def _seed_session(
    engine: Engine,
    session_id: str = "session_1",
    mode: SessionMode = SessionMode.SOCRATIC,
    status: SessionStatus = SessionStatus.ACTIVE,
) -> None:
    SqlSessionRepository(engine).add(
        Session(
            id=session_id,
            goal_id="goal_1",
            mode=mode,
            objective="Practice window functions",
            status=status,
            started_at=NOW,
        )
    )


def _service(engine: Engine, provider: object) -> TutorService:
    goals = SqlGoalRepository(engine)
    context_builder = ContextBuilder(
        goals=goals,
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        mistakes=SqlMistakeRepository(engine),
    )
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    return TutorService(
        goals=goals,
        sessions=SqlSessionRepository(engine),
        context_builder=context_builder,
        orchestrator=orchestrator,
    )


def _tutor_response(**overrides: object) -> TutorResponse:
    defaults: dict[str, object] = dict(
        mode="question",
        content="What do you think happens if two rows share the same value?",
        check_for_understanding=None,
        next_activity=None,
    )
    defaults.update(overrides)
    return TutorResponse(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_ask_returns_the_ai_response(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    _seed_session(engine)
    provider = MockProvider()
    provider.set_response(TutorResponse, _tutor_response())
    service = _service(engine, provider)

    response = await service.ask("session_1", "concept_1", [])

    assert response.mode == "question"
    assert "same value" in response.content


@pytest.mark.asyncio
async def test_ask_raises_when_session_not_found_without_calling_ai(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service = _service(engine, NeverCalledProvider())

    with pytest.raises(SessionNotFoundError):
        await service.ask("missing_session", "concept_1", [])


@pytest.mark.asyncio
async def test_ask_raises_when_session_is_not_active(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    _seed_session(engine, status=SessionStatus.COMPLETED)
    service = _service(engine, NeverCalledProvider())

    with pytest.raises(InactiveSessionError):
        await service.ask("session_1", "concept_1", [])


@pytest.mark.asyncio
async def test_ask_raises_when_session_is_not_socratic_mode(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    _seed_session(engine, mode=SessionMode.GUIDED)
    service = _service(engine, NeverCalledProvider())

    with pytest.raises(SessionNotSocraticError):
        await service.ask("session_1", "concept_1", [])


@pytest.mark.asyncio
async def test_ask_raises_when_goal_not_found_without_calling_ai(tmp_path: Path) -> None:
    # Real SQL storage FK-constrains sessions.goal_id against goals.id, so
    # this otherwise-unreachable defensive path needs fakes to exercise.
    engine = _engine(tmp_path)
    session = Session(
        id="session_1",
        goal_id="missing_goal",
        mode=SessionMode.SOCRATIC,
        objective="Practice",
        status=SessionStatus.ACTIVE,
        started_at=NOW,
    )
    context_builder = ContextBuilder(
        goals=FakeGoalRepository([]),  # type: ignore[arg-type]
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        mistakes=SqlMistakeRepository(engine),
    )
    service = TutorService(
        goals=FakeGoalRepository([]),  # type: ignore[arg-type]
        sessions=FakeSessionRepository([session]),  # type: ignore[arg-type]
        context_builder=context_builder,
        orchestrator=AIOrchestrator(
            engine, NeverCalledProvider(), provider_name="mock", model="mock-1"
        ),  # type: ignore[arg-type]
    )

    with pytest.raises(GoalNotFoundError):
        await service.ask("session_1", "concept_1", [])


@pytest.mark.asyncio
async def test_ask_sends_role_prompt_version_history_and_socratic_constraints(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    _seed_session(engine)
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> TutorResponse:
        captured.append(request)
        return _tutor_response()

    provider = MockProvider()
    provider.set_response(TutorResponse, _capture)
    service = _service(engine, provider)
    history = [
        TutorTurn(speaker="tutor", content="What have you tried so far?"),
        TutorTurn(speaker="learner", content="Not sure where to start."),
    ]

    await service.ask("session_1", "concept_1", history, message="Is it like a subquery?")

    sent = captured[0]
    assert sent.role == "tutor"
    assert sent.prompt_version == "tutor.v1"
    assert sent.goal["id"] == "goal_1"
    assert sent.task["concept_id"] == "concept_1"
    assert sent.task["learner_message"] == "Is it like a subquery?"
    assert sent.current_state["history"] == [
        {"speaker": "tutor", "content": "What have you tried so far?"},
        {"speaker": "learner", "content": "Not sure where to start."},
    ]
    assert sent.constraints["style"] == "socratic"
    assert any(item["kind"] == "concept" for item in sent.context)


@pytest.mark.asyncio
async def test_ask_defaults_message_to_empty_string_for_the_opening_turn(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    _seed_session(engine)
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> TutorResponse:
        captured.append(request)
        return _tutor_response()

    provider = MockProvider()
    provider.set_response(TutorResponse, _capture)
    service = _service(engine, provider)

    await service.ask("session_1", "concept_1", [])

    assert captured[0].task["learner_message"] == ""
