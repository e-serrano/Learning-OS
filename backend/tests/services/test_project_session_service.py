from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import ExerciseGeneratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.domain.entities import Concept, LearningGoal
from app.domain.enums import ConceptStatus, ExerciseType, GoalStatus, ProjectStatus, TargetLevel
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import (
    SqlActivityRepository,
    SqlConceptRelationRepository,
    SqlConceptRepository,
    SqlEvidenceRepository,
    SqlGoalRepository,
    SqlMistakeRepository,
    SqlProjectRepository,
    SqlSessionRepository,
)
from app.services.context_builder import ContextBuilder, GoalNotFoundError
from app.services.project_generation_service import ProjectGenerationService
from app.services.project_session_service import ProjectNotFoundError, ProjectSessionService
from app.services.project_task_service import ProjectTaskService

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
            id="window_functions",
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


def _service(engine: Engine, provider: object) -> ProjectSessionService:
    goals = SqlGoalRepository(engine)
    projects = SqlProjectRepository(engine)
    context_builder = ContextBuilder(
        goals=goals,
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        mistakes=SqlMistakeRepository(engine),
    )
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    generation = ProjectGenerationService(
        goals=goals,
        context_builder=context_builder,
        projects=projects,
        orchestrator=orchestrator,
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )
    tasks = ProjectTaskService(
        projects=projects,
        sessions=SqlSessionRepository(engine),
        activities=SqlActivityRepository(engine),
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )
    return ProjectSessionService(goals=goals, projects=projects, generation=generation, tasks=tasks)


def _generator_response(**overrides: object) -> ExerciseGeneratorResponse:
    defaults: dict[str, object] = dict(
        type=ExerciseType.DESIGN,
        difficulty=4,
        prompt="Build a small ETL pipeline that ranks top products.",
        success_criteria=["Uses at least one window function", "Handles duplicate rows"],
        hints=[],
        solution="",
        common_mistakes=[],
        transfer_variant=None,
    )
    defaults.update(overrides)
    return ExerciseGeneratorResponse(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_create_project_generates_project_and_tasks(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response())
    service = _service(engine, provider)

    result = await service.create_project("goal_1", ["window_functions"])

    assert result.project.goal_id == "goal_1"
    assert result.project.status == ProjectStatus.ACTIVE
    assert result.session.goal_id == "goal_1"
    assert len(result.tasks) == 2
    assert [t.sequence for t in result.tasks] == [1, 2]


@pytest.mark.asyncio
async def test_create_project_raises_when_goal_missing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()
    service = _service(engine, provider)

    with pytest.raises(GoalNotFoundError):
        await service.create_project("missing", ["window_functions"])


@pytest.mark.asyncio
async def test_list_projects_returns_goal_projects(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response())
    service = _service(engine, provider)
    created = await service.create_project("goal_1", ["window_functions"])

    projects = service.list_projects("goal_1")

    assert [p.id for p in projects] == [created.project.id]


def test_list_projects_raises_when_goal_missing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service = _service(engine, MockProvider())

    with pytest.raises(GoalNotFoundError):
        service.list_projects("missing")


@pytest.mark.asyncio
async def test_get_project_returns_created_project(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response())
    service = _service(engine, provider)
    created = await service.create_project("goal_1", ["window_functions"])

    fetched = service.get_project(created.project.id)

    assert fetched == created.project


def test_get_project_raises_when_missing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service = _service(engine, MockProvider())

    with pytest.raises(ProjectNotFoundError):
        service.get_project("missing")
