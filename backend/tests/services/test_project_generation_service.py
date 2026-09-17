from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import ExerciseGeneratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Concept, LearningGoal
from app.domain.enums import ConceptStatus, ExerciseType, GoalStatus, ProjectStatus, TargetLevel
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import (
    SqlConceptRelationRepository,
    SqlConceptRepository,
    SqlEvidenceRepository,
    SqlGoalRepository,
    SqlMistakeRepository,
    SqlProjectRepository,
)
from app.services.context_builder import ContextBuilder, GoalNotFoundError
from app.services.project_generation_service import MAX_TITLE_LENGTH, ProjectGenerationService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class NeverCalledProvider:
    async def generate(self, request: object, response_model: object) -> object:
        raise AssertionError("AI provider must not be called")


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _seed_goal_and_concepts(engine: Engine, concept_ids: list[str]) -> None:
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
    concepts = SqlConceptRepository(engine)
    for concept_id in concept_ids:
        concepts.add(
            Concept(
                id=concept_id,
                title=concept_id,
                domain="sql",
                status=ConceptStatus.USABLE,
                mastery=3,
                confidence=50,
                importance=3,
                retention=40,
                created_at=NOW,
                updated_at=NOW,
            )
        )


def _service(engine: Engine, provider: object) -> ProjectGenerationService:
    goals = SqlGoalRepository(engine)
    context_builder = ContextBuilder(
        goals=goals,
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        mistakes=SqlMistakeRepository(engine),
    )
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    return ProjectGenerationService(
        goals=goals,
        context_builder=context_builder,
        projects=SqlProjectRepository(engine),
        orchestrator=orchestrator,
        clock=_FixedClock(),
        ids=_FakeIdGenerator(),
    )


class _FixedClock:
    def now(self) -> datetime:
        return NOW


class _FakeIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


def _generator_response(**overrides: object) -> ExerciseGeneratorResponse:
    defaults: dict[str, object] = dict(
        type=ExerciseType.DESIGN,
        difficulty=4,
        prompt=(
            "Build a small ETL pipeline that loads sales data and ranks top products.\n"
            "Use window functions."
        ),
        success_criteria=["Uses at least one window function", "Handles duplicate rows"],
        hints=[],
        solution="",
        common_mistakes=[],
        transfer_variant=None,
    )
    defaults.update(overrides)
    return ExerciseGeneratorResponse(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_generate_project_returns_project_built_from_ai_response(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concepts(engine, ["window_functions"])
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response())
    service = _service(engine, provider)

    project = await service.generate_project("goal_1", ["window_functions"])

    assert (
        project.title == "Build a small ETL pipeline that loads sales data and ranks top products."
    )
    assert project.objective == _generator_response().prompt
    assert project.difficulty == 4
    assert project.status == ProjectStatus.PROPOSED
    assert project.concept_ids == ["window_functions"]
    assert project.success_criteria == [
        "Uses at least one window function",
        "Handles duplicate rows",
    ]


@pytest.mark.asyncio
async def test_generate_project_persists_via_project_repository(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concepts(engine, ["window_functions"])
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response())
    service = _service(engine, provider)

    created = await service.generate_project("goal_1", ["window_functions"])

    assert SqlProjectRepository(engine).get(created.id) == created


@pytest.mark.asyncio
async def test_generate_project_raises_when_goal_not_found_without_calling_ai(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    service = _service(engine, NeverCalledProvider())

    with pytest.raises(GoalNotFoundError):
        await service.generate_project("missing_goal", ["window_functions"])


@pytest.mark.asyncio
async def test_generate_project_merges_context_across_concepts_with_one_goal_item(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concepts(engine, ["window_functions", "subqueries"])
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> ExerciseGeneratorResponse:
        captured.append(request)
        return _generator_response()

    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _capture)
    service = _service(engine, provider)

    await service.generate_project("goal_1", ["window_functions", "subqueries"])

    sent = captured[0]
    goal_items = [item for item in sent.context if item["kind"] == "goal"]
    concept_items = [item for item in sent.context if item["kind"] == "concept"]
    assert len(goal_items) == 1
    assert {item["id"] for item in concept_items} == {"window_functions", "subqueries"}
    assert sent.task["assessment_type"] == "project"
    assert sent.task["concept_ids"] == ["window_functions", "subqueries"]


@pytest.mark.asyncio
async def test_generate_project_truncates_a_very_long_title(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concepts(engine, ["window_functions"])
    long_prompt = "x" * (MAX_TITLE_LENGTH + 50)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response(prompt=long_prompt))
    service = _service(engine, provider)

    project = await service.generate_project("goal_1", ["window_functions"])

    assert len(project.title) == MAX_TITLE_LENGTH
    assert project.objective == long_prompt
