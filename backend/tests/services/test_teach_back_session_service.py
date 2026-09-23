from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import ExerciseGeneratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.domain.entities import Concept, LearningGoal
from app.domain.enums import (
    ActivityStatus,
    ConceptStatus,
    ExerciseType,
    GoalStatus,
    SessionMode,
    TargetLevel,
)
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import (
    SqlActivityRepository,
    SqlConceptRelationRepository,
    SqlConceptRepository,
    SqlEvidenceRepository,
    SqlExerciseRepository,
    SqlGoalRepository,
    SqlMistakeRepository,
    SqlSessionRepository,
)
from app.services.context_builder import ContextBuilder, GoalNotFoundError
from app.services.teach_back_service import TeachBackService
from app.services.teach_back_session_service import (
    ActivityNotATeachBackError,
    TeachBackNotFoundError,
    TeachBackSessionService,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class _FixedClock:
    def now(self) -> datetime:
        return NOW


class _FakeIdGenerator:
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


def _generator_response(**overrides: object) -> ExerciseGeneratorResponse:
    defaults: dict[str, object] = dict(
        type=ExerciseType.MCQ,
        difficulty=2,
        prompt="Explain window functions as if teaching a beginner.",
        success_criteria=["Covers the OVER clause"],
        hints=[],
        solution="A model explanation.",
        common_mistakes=[],
        transfer_variant=None,
    )
    defaults.update(overrides)
    return ExerciseGeneratorResponse(**defaults)  # type: ignore[arg-type]


def _service(engine: Engine, provider: object) -> TeachBackSessionService:
    goals = SqlGoalRepository(engine)
    context_builder = ContextBuilder(
        goals=goals,
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        mistakes=SqlMistakeRepository(engine),
    )
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    teach_back = TeachBackService(
        goals=goals,
        context_builder=context_builder,
        exercises=SqlExerciseRepository(engine),
        orchestrator=orchestrator,
        clock=_FixedClock(),
        ids=_FakeIdGenerator(),
    )
    return TeachBackSessionService(
        sessions=SqlSessionRepository(engine),
        activities=SqlActivityRepository(engine),
        exercises=SqlExerciseRepository(engine),
        teach_back=teach_back,
        clock=_FixedClock(),
        ids=_FakeIdGenerator(),
    )


@pytest.mark.asyncio
async def test_create_teach_back_creates_a_socratic_free_teach_back_session(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response())
    service = _service(engine, provider)

    result = await service.create_teach_back("goal_1", "concept_1")

    assert result.session.mode == SessionMode.TEACH_BACK
    assert result.session.goal_id == "goal_1"
    assert result.activity.session_id == result.session.id
    assert result.activity.concept_ids == ["concept_1"]
    assert result.activity.status == ActivityStatus.ACTIVE
    assert result.activity.exercise_id == result.exercise.id
    assert result.exercise.type == ExerciseType.TEACH_BACK


@pytest.mark.asyncio
async def test_create_teach_back_raises_when_goal_not_found(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response())
    service = _service(engine, provider)

    with pytest.raises(GoalNotFoundError):
        await service.create_teach_back("missing_goal", "concept_1")


@pytest.mark.asyncio
async def test_get_teach_back_returns_the_created_result(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response())
    service = _service(engine, provider)
    created = await service.create_teach_back("goal_1", "concept_1")

    fetched = service.get_teach_back(created.activity.id)

    assert fetched.session.id == created.session.id
    assert fetched.exercise.id == created.exercise.id


def test_get_teach_back_raises_when_activity_missing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service = _service(engine, MockProvider())

    with pytest.raises(TeachBackNotFoundError):
        service.get_teach_back("missing_activity")


@pytest.mark.asyncio
async def test_get_teach_back_raises_for_an_activity_from_a_non_teach_back_session(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response())
    service = _service(engine, provider)
    created = await service.create_teach_back("goal_1", "concept_1")
    # Flip the owning session's mode away from teach_back after the fact.
    sessions = SqlSessionRepository(engine)
    sessions.update(created.session.model_copy(update={"mode": SessionMode.GUIDED}))

    with pytest.raises(ActivityNotATeachBackError):
        service.get_teach_back(created.activity.id)
