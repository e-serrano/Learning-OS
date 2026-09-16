from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import HighLeverageConcept, PlannerResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Concept, LearningGoal
from app.domain.enums import ConceptStatus, GoalStatus, TargetLevel
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import SqlConceptRepository, SqlGoalRepository
from app.services.context_builder import GoalNotFoundError
from app.services.planner_service import PlannerService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class NeverCalledProvider:
    async def generate(self, request: object, response_model: object) -> object:
        raise AssertionError("AI provider must not be called")


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _seed_goal(engine: Engine, **overrides: object) -> None:
    defaults: dict[str, object] = dict(
        id="goal_1",
        title="Learn BigQuery",
        description="Get to production-ready SQL",
        target_level=TargetLevel.PROFESSIONAL,
        status=GoalStatus.ACTIVE,
        priority=3,
        available_minutes_per_week=180,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    SqlGoalRepository(engine).add(LearningGoal(**defaults))  # type: ignore[arg-type]


def _service(engine: Engine, provider: object) -> PlannerService:
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    return PlannerService(
        goals=SqlGoalRepository(engine),
        concepts=SqlConceptRepository(engine),
        orchestrator=orchestrator,
    )


@pytest.mark.asyncio
async def test_plan_returns_the_three_planner_fields(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    expected = PlannerResponse(
        high_leverage_concepts=[
            HighLeverageConcept(
                concept_id="window_functions",
                title="Window Functions",
                importance=5,
                reason="Used everywhere in analytics SQL",
            )
        ],
        deferred_topics=["recursive_ctes"],
        roadmap_nodes=[{"id": "window_functions"}],
        roadmap_edges=[],
        diagnostic_focus=["window_functions"],
    )
    provider = MockProvider()
    provider.set_response(PlannerResponse, expected)
    service = _service(engine, provider)

    result = await service.plan("goal_1")

    assert result.high_leverage_concepts == expected.high_leverage_concepts
    assert result.deferred_topics == expected.deferred_topics
    assert result.diagnostic_focus == expected.diagnostic_focus
    assert result.roadmap_nodes == expected.roadmap_nodes
    assert result.roadmap_edges == expected.roadmap_edges


@pytest.mark.asyncio
async def test_plan_raises_when_goal_not_found_without_calling_ai(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service = _service(engine, NeverCalledProvider())

    with pytest.raises(GoalNotFoundError):
        await service.plan("missing_goal")


@pytest.mark.asyncio
async def test_plan_sends_empty_existing_knowledge_for_a_brand_new_goal(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> PlannerResponse:
        captured.append(request)
        return PlannerResponse()

    provider = MockProvider()
    provider.set_response(PlannerResponse, _capture)
    service = _service(engine, provider)

    await service.plan("goal_1")

    assert captured[0].current_state["existing_knowledge"] == []


@pytest.mark.asyncio
async def test_plan_includes_existing_concepts_linked_to_the_goal(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    concepts = SqlConceptRepository(engine)
    concepts.add(
        Concept(
            id="select_basics",
            title="SELECT basics",
            domain="sql",
            status=ConceptStatus.MASTERED,
            mastery=5,
            confidence=100,
            importance=3,
            retention=100,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    concepts.link_to_goal("goal_1", "select_basics")
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> PlannerResponse:
        captured.append(request)
        return PlannerResponse()

    provider = MockProvider()
    provider.set_response(PlannerResponse, _capture)
    service = _service(engine, provider)

    await service.plan("goal_1")

    existing = captured[0].current_state["existing_knowledge"]
    assert existing == [
        {
            "concept_id": "select_basics",
            "title": "SELECT basics",
            "mastery": 5.0,
            "status": "mastered",
        }
    ]


@pytest.mark.asyncio
async def test_plan_sends_goal_and_available_time_in_the_request(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> PlannerResponse:
        captured.append(request)
        return PlannerResponse()

    provider = MockProvider()
    provider.set_response(PlannerResponse, _capture)
    service = _service(engine, provider)

    await service.plan("goal_1")

    sent = captured[0]
    assert sent.role == "planner"
    assert sent.prompt_version == "planner.v1"
    assert sent.goal["id"] == "goal_1"
    assert sent.goal["target_level"] == "professional"
    assert sent.task["available_minutes_per_week"] == 180
