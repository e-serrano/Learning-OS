from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import DiagnosticianResponse, DiagnosticItem
from app.ai.errors import AIProviderUnavailableError
from app.ai.orchestrator import AIOrchestrator
from app.api.dependencies import get_diagnostic_session_service
from app.domain.entities import Concept, LearningGoal
from app.domain.enums import ConceptStatus, GoalStatus, TargetLevel
from app.main import app
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import (
    SqlActivityRepository,
    SqlConceptRelationRepository,
    SqlConceptRepository,
    SqlEvidenceRepository,
    SqlGoalRepository,
    SqlMistakeRepository,
    SqlSessionRepository,
)
from app.services.context_builder import ContextBuilder
from app.services.diagnostic_service import DiagnosticService
from app.services.diagnostic_session_service import DiagnosticSessionService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class FakeIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


class FailingProvider:
    async def generate(self, request: object, response_model: object) -> object:
        raise AIProviderUnavailableError("provider is down")


def _response(**overrides: object) -> DiagnosticianResponse:
    defaults: dict[str, object] = dict(
        items=[
            DiagnosticItem(
                concept_id="window_functions",
                evidence_type="recall",
                question="What does ROW_NUMBER() do?",
                difficulty=2,
            )
        ]
    )
    defaults.update(overrides)
    return DiagnosticianResponse(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def engine(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _build_service(engine, provider: object) -> DiagnosticSessionService:  # type: ignore[no-untyped-def]
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    context_builder = ContextBuilder(
        goals=SqlGoalRepository(engine),
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        mistakes=SqlMistakeRepository(engine),
    )
    diagnostic = DiagnosticService(
        goals=SqlGoalRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        context_builder=context_builder,
        orchestrator=orchestrator,
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )
    return DiagnosticSessionService(
        goals=SqlGoalRepository(engine),
        concepts=SqlConceptRepository(engine),
        sessions=SqlSessionRepository(engine),
        activities=SqlActivityRepository(engine),
        diagnostic=diagnostic,
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )


@pytest.fixture
def client(engine):  # type: ignore[no-untyped-def]
    provider = MockProvider()
    provider.set_response(DiagnosticianResponse, _response())
    service = _build_service(engine, provider)
    app.dependency_overrides[get_diagnostic_session_service] = lambda: service
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def _seed_goal(engine, goal_id: str = "goal_1") -> None:  # type: ignore[no-untyped-def]
    SqlGoalRepository(engine).add(
        LearningGoal(
            id=goal_id,
            title="Learn SQL",
            target_level=TargetLevel.PROFESSIONAL,
            status=GoalStatus.ACTIVE,
            priority=3,
            created_at=NOW,
            updated_at=NOW,
        )
    )


def _seed_concept(engine, concept_id: str, goal_id: str = "goal_1") -> None:  # type: ignore[no-untyped-def]
    concepts = SqlConceptRepository(engine)
    concepts.add(
        Concept(
            id=concept_id,
            title=concept_id,
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
    concepts.link_to_goal(goal_id, concept_id)


def test_start_diagnostic_returns_session_and_items(client: TestClient, engine) -> None:  # type: ignore[no-untyped-def]
    _seed_goal(engine)
    _seed_concept(engine, "window_functions")

    response = client.post("/api/v1/goals/goal_1/diagnostic/start")

    assert response.status_code == 200
    body = response.json()
    assert body["goal_id"] == "goal_1"
    assert body["status"] == "active"
    assert len(body["items"]) == 1
    assert body["items"][0]["question"] == "What does ROW_NUMBER() do?"


def test_start_diagnostic_404s_when_goal_missing(client: TestClient) -> None:
    response = client.post("/api/v1/goals/missing/diagnostic/start")

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_start_diagnostic_conflicts_when_no_concepts(client: TestClient, engine) -> None:  # type: ignore[no-untyped-def]
    _seed_goal(engine)

    response = client.post("/api/v1/goals/goal_1/diagnostic/start")

    assert response.status_code == 409
    assert response.json()["detail"]["error"]["code"] == "SESSION_STATE_ERROR"


def test_start_diagnostic_maps_provider_unavailable(tmp_path: Path) -> None:
    engine = create_sqlite_engine(str(tmp_path / "test2.sqlite3"))
    Base.metadata.create_all(engine)
    _seed_goal(engine)
    _seed_concept(engine, "window_functions")
    service = _build_service(engine, FailingProvider())

    app.dependency_overrides[get_diagnostic_session_service] = lambda: service
    test_client = TestClient(app)
    try:
        response = test_client.post("/api/v1/goals/goal_1/diagnostic/start")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["error"]["code"] == "AI_UNAVAILABLE"
