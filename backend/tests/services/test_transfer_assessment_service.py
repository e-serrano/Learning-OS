from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import ExerciseGeneratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Concept, Exercise, LearningGoal
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
from app.services.context_builder import ContextBuilder, GoalNotFoundError
from app.services.transfer_assessment_service import TransferAssessmentService

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
            id="window_functions",
            title="Window Functions",
            domain="sql",
            status=ConceptStatus.USABLE,
            mastery=3,
            confidence=50,
            importance=4,
            retention=40,
            created_at=NOW,
            updated_at=NOW,
        )
    )


def _service(engine: Engine, provider: object) -> TransferAssessmentService:
    goals = SqlGoalRepository(engine)
    context_builder = ContextBuilder(
        goals=goals,
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        mistakes=SqlMistakeRepository(engine),
    )
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    return TransferAssessmentService(
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
        type=ExerciseType.SCENARIO,
        difficulty=4,
        prompt="Given a new logistics dataset, rank shipments per warehouse.",
        success_criteria=["Uses a window function", "Applies to the new domain"],
        hints=[],
        solution="SELECT RANK() OVER (...) FROM shipments;",
        common_mistakes=[],
        transfer_variant=None,
    )
    defaults.update(overrides)
    return ExerciseGeneratorResponse(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_generate_transfer_scenario_returns_exercise_from_ai_response(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response())
    service = _service(engine, provider)

    exercise = await service.generate_transfer_scenario("goal_1", "window_functions")

    assert exercise.concept_ids == ["window_functions"]
    assert exercise.prompt == "Given a new logistics dataset, rank shipments per warehouse."
    assert exercise.type == ExerciseType.SCENARIO


@pytest.mark.asyncio
async def test_generate_transfer_scenario_persists_via_exercise_repository(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response())
    service = _service(engine, provider)

    created = await service.generate_transfer_scenario("goal_1", "window_functions")

    assert SqlExerciseRepository(engine).get(created.id) == created


@pytest.mark.asyncio
async def test_generate_transfer_scenario_raises_when_goal_not_found_without_calling_ai(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    service = _service(engine, NeverCalledProvider())

    with pytest.raises(GoalNotFoundError):
        await service.generate_transfer_scenario("missing_goal", "window_functions")


@pytest.mark.asyncio
async def test_generate_transfer_scenario_sends_transfer_instruction_and_empty_prior_list(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> ExerciseGeneratorResponse:
        captured.append(request)
        return _generator_response()

    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _capture)
    service = _service(engine, provider)

    await service.generate_transfer_scenario("goal_1", "window_functions")

    sent = captured[0]
    assert sent.task["assessment_type"] == "transfer"
    assert "transfer" in sent.task["instruction"].lower()
    assert sent.task["prior_exercise_prompts"] == []


@pytest.mark.asyncio
async def test_generate_transfer_scenario_includes_prior_exercise_prompts_to_avoid(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    exercises = SqlExerciseRepository(engine)
    exercises.add(
        Exercise(
            id="exercise_prior",
            type=ExerciseType.SQL,
            difficulty=3,
            goal_id="goal_1",
            concept_ids=["window_functions"],
            prompt="Write a query using ROW_NUMBER().",
            solution="SELECT ROW_NUMBER() OVER (...) FROM t;",
            created_at=NOW,
        )
    )
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> ExerciseGeneratorResponse:
        captured.append(request)
        return _generator_response()

    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _capture)
    service = _service(engine, provider)

    await service.generate_transfer_scenario("goal_1", "window_functions")

    assert captured[0].task["prior_exercise_prompts"] == ["Write a query using ROW_NUMBER()."]
