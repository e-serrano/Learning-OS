from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import PlannerResponse
from app.ai.errors import AIProviderUnavailableError
from app.ai.orchestrator import AIOrchestrator
from app.api.dependencies import get_roadmap_generation_service, get_roadmap_service
from app.domain.entities import LearningGoal
from app.domain.enums import GoalStatus, TargetLevel
from app.main import app
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import (
    SqlConceptRelationRepository,
    SqlConceptRepository,
    SqlGoalRepository,
    SqlRoadmapRepository,
)
from app.services.planner_service import PlannerService
from app.services.roadmap_generation_service import RoadmapGenerationService
from app.services.roadmap_service import RoadmapService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FailingProvider:
    async def generate(self, request: object, response_model: object) -> object:
        raise AIProviderUnavailableError("provider is down")


class FakeClock:
    def now(self) -> datetime:
        return NOW


class FakeIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


def _planner_response(**overrides: object) -> PlannerResponse:
    defaults: dict[str, object] = dict(
        high_leverage_concepts=[],
        deferred_topics=[],
        roadmap_nodes=[
            {"id": "select_basics", "title": "SELECT basics"},
            {"id": "window_functions", "title": "Window Functions"},
        ],
        roadmap_edges=[{"source": "select_basics", "target": "window_functions"}],
        diagnostic_focus=[],
    )
    defaults.update(overrides)
    return PlannerResponse(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def engine(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _roadmap_service(engine) -> RoadmapService:  # type: ignore[no-untyped-def]
    return RoadmapService(
        goals=SqlGoalRepository(engine),
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        roadmaps=SqlRoadmapRepository(engine),
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )


@pytest.fixture
def client(engine):  # type: ignore[no-untyped-def]
    provider = MockProvider()
    provider.set_response(PlannerResponse, _planner_response())
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")
    planner = PlannerService(SqlGoalRepository(engine), SqlConceptRepository(engine), orchestrator)
    roadmap_service = _roadmap_service(engine)
    generation_service = RoadmapGenerationService(planner, roadmap_service)

    app.dependency_overrides[get_roadmap_service] = lambda: roadmap_service
    app.dependency_overrides[get_roadmap_generation_service] = lambda: generation_service
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def _seed_goal(engine, goal_id: str = "goal_1") -> None:  # type: ignore[no-untyped-def]
    SqlGoalRepository(engine).add(
        LearningGoal(
            id=goal_id,
            title="Learn BigQuery",
            domain="sql",
            target_level=TargetLevel.PROFESSIONAL,
            status=GoalStatus.ACTIVE,
            priority=3,
            created_at=NOW,
            updated_at=NOW,
        )
    )


def test_generate_roadmap_returns_the_graph(client: TestClient, engine) -> None:  # type: ignore[no-untyped-def]
    _seed_goal(engine)

    response = client.post("/api/v1/goals/goal_1/roadmap/generate")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 1
    assert body["status"] == "active"
    ids = {n["id"] for n in body["nodes"]}
    assert ids == {"select_basics", "window_functions"}
    assert len(body["edges"]) == 1


def test_generate_roadmap_404s_when_goal_missing(client: TestClient) -> None:
    response = client.post("/api/v1/goals/missing/roadmap/generate")

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_get_roadmap_returns_generated_graph(client: TestClient, engine) -> None:  # type: ignore[no-untyped-def]
    _seed_goal(engine)
    client.post("/api/v1/goals/goal_1/roadmap/generate")

    response = client.get("/api/v1/goals/goal_1/roadmap")

    assert response.status_code == 200
    assert response.json()["version"] == 1


def test_get_roadmap_404s_when_none_generated_yet(client: TestClient, engine) -> None:  # type: ignore[no-untyped-def]
    _seed_goal(engine)

    response = client.get("/api/v1/goals/goal_1/roadmap")

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_recalculate_roadmap_supersedes_the_previous_version(client: TestClient, engine) -> None:  # type: ignore[no-untyped-def]
    _seed_goal(engine)
    client.post("/api/v1/goals/goal_1/roadmap/generate")

    response = client.post("/api/v1/goals/goal_1/roadmap/recalculate")

    assert response.status_code == 200
    assert response.json()["version"] == 2


def test_generate_roadmap_maps_provider_unavailable(tmp_path: Path) -> None:
    engine = create_sqlite_engine(str(tmp_path / "test2.sqlite3"))
    Base.metadata.create_all(engine)
    _seed_goal(engine)

    orchestrator = AIOrchestrator(engine, FailingProvider(), provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    planner = PlannerService(SqlGoalRepository(engine), SqlConceptRepository(engine), orchestrator)
    roadmap_service = _roadmap_service(engine)
    generation_service = RoadmapGenerationService(planner, roadmap_service)

    app.dependency_overrides[get_roadmap_service] = lambda: roadmap_service
    app.dependency_overrides[get_roadmap_generation_service] = lambda: generation_service
    test_client = TestClient(app)
    try:
        response = test_client.post("/api/v1/goals/goal_1/roadmap/generate")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["error"]["code"] == "AI_UNAVAILABLE"
