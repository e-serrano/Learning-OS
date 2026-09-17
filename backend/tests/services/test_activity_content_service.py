from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import ExerciseGeneratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.domain.entities import Activity, Concept, LearningGoal, Session
from app.domain.enums import (
    ActivityStatus,
    ActivityType,
    ConceptStatus,
    ExerciseType,
    GoalStatus,
    SessionMode,
    SessionStatus,
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
from app.services.activity_content_service import ActivityContentService
from app.services.context_builder import ContextBuilder
from app.services.exercise_generator_service import ExerciseGeneratorService

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
    SqlSessionRepository(engine).add(
        Session(
            id="session_1",
            goal_id="goal_1",
            mode=SessionMode.GUIDED,
            objective="Practice",
            status=SessionStatus.ACTIVE,
            started_at=NOW,
        )
    )


def _seed_activity(engine: Engine) -> Activity:
    activity = Activity(
        id="activity_1",
        session_id="session_1",
        type=ActivityType.EXERCISE,
        sequence=1,
        concept_ids=["window_functions"],
        status=ActivityStatus.ACTIVE,
    )
    SqlActivityRepository(engine).add(activity)
    return activity


def _service(engine: Engine, provider: object) -> ActivityContentService:
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    context_builder = ContextBuilder(
        goals=SqlGoalRepository(engine),
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        mistakes=SqlMistakeRepository(engine),
    )
    generator = ExerciseGeneratorService(
        goals=SqlGoalRepository(engine),
        context_builder=context_builder,
        exercises=SqlExerciseRepository(engine),
        orchestrator=orchestrator,
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )
    return ActivityContentService(SqlActivityRepository(engine), generator)


def _response(**overrides: object) -> ExerciseGeneratorResponse:
    defaults: dict[str, object] = dict(
        type=ExerciseType.CODING,
        difficulty=3,
        prompt="Write a query using ROW_NUMBER().",
        success_criteria=["Uses ROW_NUMBER()"],
        hints=[],
        solution="SELECT ROW_NUMBER() OVER (ORDER BY id) FROM t;",
        common_mistakes=[],
    )
    defaults.update(overrides)
    return ExerciseGeneratorResponse(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_attach_exercise_generates_and_persists_the_pairing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    activity = _seed_activity(engine)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _response())

    result = await _service(engine, provider).attach_exercise("goal_1", activity)

    assert result.exercise.concept_ids == ["window_functions"]
    assert result.activity.exercise_id == result.exercise.id
    stored = SqlActivityRepository(engine).get("activity_1")
    assert stored is not None
    assert stored.exercise_id == result.exercise.id
