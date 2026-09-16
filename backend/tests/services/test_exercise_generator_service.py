from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import ExerciseGeneratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Concept, LearningGoal
from app.domain.enums import ConceptStatus, ExerciseType, GoalStatus, TargetLevel
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import (
    SqlConceptRelationRepository,
    SqlConceptRepository,
    SqlEvidenceRepository,
    SqlExerciseRepository,
    SqlGoalRepository,
    SqlMistakeRepository,
)
from app.services.context_builder import ConceptNotFoundError, ContextBuilder, GoalNotFoundError
from app.services.exercise_generator_service import ExerciseGeneratorService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class NeverCalledProvider:
    async def generate(self, request: object, response_model: object) -> object:
        raise AssertionError("AI provider must not be called")


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


def _service(engine: Engine, provider: object) -> ExerciseGeneratorService:
    goals = SqlGoalRepository(engine)
    context_builder = ContextBuilder(
        goals=goals,
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        mistakes=SqlMistakeRepository(engine),
    )
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    return ExerciseGeneratorService(
        goals=goals,
        context_builder=context_builder,
        exercises=SqlExerciseRepository(engine),
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
        type=ExerciseType.SQL,
        difficulty=3,
        prompt="Write a query using ROW_NUMBER().",
        success_criteria=["Uses ROW_NUMBER()", "Handles ties correctly"],
        hints=["Think about PARTITION BY"],
        solution="SELECT ROW_NUMBER() OVER (...) FROM t;",
        common_mistakes=["Forgetting ORDER BY inside OVER()"],
        transfer_variant="Now do the same with RANK().",
    )
    defaults.update(overrides)
    return ExerciseGeneratorResponse(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_generate_returns_exercise_built_from_ai_response(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response())
    service = _service(engine, provider)

    exercise = await service.generate("goal_1", "concept_1")

    assert exercise.type == ExerciseType.SQL
    assert exercise.difficulty == 3
    assert exercise.goal_id == "goal_1"
    assert exercise.concept_ids == ["concept_1"]
    assert exercise.prompt == "Write a query using ROW_NUMBER()."
    assert exercise.success_criteria == ["Uses ROW_NUMBER()", "Handles ties correctly"]
    assert exercise.hints == ["Think about PARTITION BY"]
    assert exercise.solution == "SELECT ROW_NUMBER() OVER (...) FROM t;"
    assert exercise.common_mistakes == ["Forgetting ORDER BY inside OVER()"]
    assert exercise.transfer_variant == "Now do the same with RANK()."
    assert exercise.created_at == NOW


@pytest.mark.asyncio
async def test_generate_persists_via_exercise_repository(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response())
    service = _service(engine, provider)

    created = await service.generate("goal_1", "concept_1")

    stored = SqlExerciseRepository(engine).get(created.id)
    assert stored == created


@pytest.mark.asyncio
async def test_generate_raises_when_goal_not_found_without_calling_ai(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service = _service(engine, NeverCalledProvider())

    with pytest.raises(GoalNotFoundError):
        await service.generate("missing_goal", "concept_1")


@pytest.mark.asyncio
async def test_generate_raises_when_concept_not_found_without_calling_ai(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
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
    service = _service(engine, NeverCalledProvider())

    with pytest.raises(ConceptNotFoundError):
        await service.generate("goal_1", "missing_concept")


@pytest.mark.asyncio
async def test_generate_sends_goal_and_task_in_the_request(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> ExerciseGeneratorResponse:
        captured.append(request)
        return _generator_response()

    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _capture)
    service = _service(engine, provider)

    await service.generate("goal_1", "concept_1")

    sent = captured[0]
    assert sent.role == "exercise_generator"
    assert sent.prompt_version == "exercise_generator.v1"
    assert sent.goal["id"] == "goal_1"
    assert sent.task["concept_id"] == "concept_1"
    assert any(item["kind"] == "concept" for item in sent.context)
