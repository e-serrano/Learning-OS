from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import PlannerResponse
from app.ai.orchestrator import AIOrchestrator
from app.domain.entities import LearningGoal
from app.domain.enums import ConceptRelationType, GoalStatus, TargetLevel
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
from app.services.roadmap_service import RoadmapService, RoadmapValidationError

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


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _seed_goal(engine: Engine, **overrides: object) -> None:
    defaults: dict[str, object] = dict(
        id="goal_1",
        title="Learn BigQuery",
        domain="sql",
        target_level=TargetLevel.PROFESSIONAL,
        status=GoalStatus.ACTIVE,
        priority=3,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    SqlGoalRepository(engine).add(LearningGoal(**defaults))  # type: ignore[arg-type]


def _service(engine: Engine, provider: object) -> RoadmapGenerationService:
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    planner = PlannerService(SqlGoalRepository(engine), SqlConceptRepository(engine), orchestrator)
    roadmaps = RoadmapService(
        goals=SqlGoalRepository(engine),
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        roadmaps=SqlRoadmapRepository(engine),
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )
    return RoadmapGenerationService(planner, roadmaps)


def _planner_response(**overrides: object) -> PlannerResponse:
    defaults: dict[str, object] = dict(
        high_leverage_concepts=[],
        deferred_topics=[],
        roadmap_nodes=[
            {"id": "select_basics", "title": "SELECT basics"},
            {"id": "window_functions", "title": "Window Functions", "importance": 5},
        ],
        roadmap_edges=[
            {"source": "select_basics", "target": "window_functions", "relation": "PREREQUISITE_OF"}
        ],
        diagnostic_focus=[],
    )
    defaults.update(overrides)
    return PlannerResponse(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_generate_roadmap_builds_concepts_and_relations(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    provider = MockProvider()
    provider.set_response(PlannerResponse, _planner_response())

    roadmap = await _service(engine, provider).generate_roadmap("goal_1")

    concepts = SqlConceptRepository(engine).list_by_goal("goal_1")
    assert {c.id for c in concepts} == {"select_basics", "window_functions"}
    relations = SqlConceptRelationRepository(engine).list_relations_from("select_basics")
    assert [(r.target_id, r.relation) for r in relations] == [
        ("window_functions", ConceptRelationType.PREREQUISITE_OF)
    ]
    assert roadmap.version == 1


@pytest.mark.asyncio
async def test_generate_roadmap_defaults_missing_optional_fields(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    provider = MockProvider()
    provider.set_response(
        PlannerResponse,
        _planner_response(
            roadmap_nodes=[{"id": "a", "title": "A"}, {"id": "a_2", "title": "A2"}],
            roadmap_edges=[{"source": "a", "target": "a_2"}],
        ),
    )

    roadmap = await _service(engine, provider).generate_roadmap("goal_1")

    concept = SqlConceptRepository(engine).get("a")
    assert concept is not None
    assert concept.importance == 3
    relations = SqlConceptRelationRepository(engine).list_relations_from("a")
    assert relations[0].relation == ConceptRelationType.PREREQUISITE_OF
    assert roadmap.version == 1


@pytest.mark.asyncio
async def test_generate_roadmap_raises_on_node_missing_id(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    provider = MockProvider()
    provider.set_response(
        PlannerResponse, _planner_response(roadmap_nodes=[{"title": "No id"}], roadmap_edges=[])
    )

    with pytest.raises(RoadmapValidationError):
        await _service(engine, provider).generate_roadmap("goal_1")


@pytest.mark.asyncio
async def test_generate_roadmap_raises_on_edge_missing_source(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    provider = MockProvider()
    provider.set_response(
        PlannerResponse,
        _planner_response(
            roadmap_nodes=[{"id": "a", "title": "A"}],
            roadmap_edges=[{"target": "a"}],
        ),
    )

    with pytest.raises(RoadmapValidationError):
        await _service(engine, provider).generate_roadmap("goal_1")


@pytest.mark.asyncio
async def test_recalculating_supersedes_the_previous_roadmap(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    provider = MockProvider()
    provider.set_response(PlannerResponse, _planner_response())
    service = _service(engine, provider)
    first = await service.generate_roadmap("goal_1")

    second = await service.generate_roadmap("goal_1")

    assert second.version == first.version + 1
    roadmaps = SqlRoadmapRepository(engine)
    assert roadmaps.get_active_for_goal("goal_1") == second
