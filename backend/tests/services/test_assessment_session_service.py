from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import ExerciseGeneratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.domain.entities import Concept, LearningGoal
from app.domain.enums import ConceptStatus, ExerciseType, GoalStatus, TargetLevel
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
from app.services.assessment_session_service import (
    ActivityNotAnAssessmentError,
    AssessmentNotFoundError,
    AssessmentSessionService,
)
from app.services.context_builder import ContextBuilder, GoalNotFoundError
from app.services.transfer_assessment_service import TransferAssessmentService

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


def _seed_goal(engine: Engine) -> None:
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


def _seed_concept(engine: Engine, concept_id: str) -> None:
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
    concepts.link_to_goal("goal_1", concept_id)


def _service(engine: Engine, provider: object) -> AssessmentSessionService:
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    context_builder = ContextBuilder(
        goals=SqlGoalRepository(engine),
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        mistakes=SqlMistakeRepository(engine),
    )
    transfer_assessment = TransferAssessmentService(
        goals=SqlGoalRepository(engine),
        context_builder=context_builder,
        exercises=SqlExerciseRepository(engine),
        orchestrator=orchestrator,
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )
    return AssessmentSessionService(
        sessions=SqlSessionRepository(engine),
        activities=SqlActivityRepository(engine),
        exercises=SqlExerciseRepository(engine),
        transfer_assessment=transfer_assessment,
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )


def _response(**overrides: object) -> ExerciseGeneratorResponse:
    defaults: dict[str, object] = dict(
        type=ExerciseType.SCENARIO,
        difficulty=3,
        prompt="Apply window functions to a new dataset.",
        success_criteria=["Uses RANK() correctly"],
        hints=[],
        solution="SELECT RANK() OVER (...) FROM shipments;",
        common_mistakes=[],
        transfer_variant="new-domain",
    )
    defaults.update(overrides)
    return ExerciseGeneratorResponse(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_create_assessment_creates_session_and_activity(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    _seed_concept(engine, "window_functions")
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _response())

    result = await _service(engine, provider).create_assessment("goal_1", "window_functions")

    assert result.session.goal_id == "goal_1"
    assert result.session.status.value == "active"
    assert result.activity.session_id == result.session.id
    assert result.activity.concept_ids == ["window_functions"]
    assert result.activity.exercise_id == result.exercise.id
    assert result.exercise.prompt == "Apply window functions to a new dataset."


@pytest.mark.asyncio
async def test_create_assessment_raises_when_goal_missing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()

    with pytest.raises(GoalNotFoundError):
        await _service(engine, provider).create_assessment("missing", "window_functions")


@pytest.mark.asyncio
async def test_get_assessment_returns_created_assessment(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    _seed_concept(engine, "window_functions")
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _response())
    service = _service(engine, provider)
    created = await service.create_assessment("goal_1", "window_functions")

    result = service.get_assessment(created.activity.id)

    assert result.activity.id == created.activity.id
    assert result.session.id == created.session.id
    assert result.exercise.id == created.exercise.id


def test_get_assessment_raises_when_missing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()

    with pytest.raises(AssessmentNotFoundError):
        _service(engine, provider).get_assessment("missing")


@pytest.mark.asyncio
async def test_get_assessment_raises_when_activity_is_not_an_assessment(tmp_path: Path) -> None:
    from app.domain.entities import Activity, Session
    from app.domain.enums import ActivityStatus, ActivityType, SessionMode, SessionStatus

    engine = _engine(tmp_path)
    _seed_goal(engine)
    sessions = SqlSessionRepository(engine)
    activities = SqlActivityRepository(engine)
    sessions.add(
        Session(
            id="session_1",
            goal_id="goal_1",
            mode=SessionMode.PRACTICE,
            objective="Practice",
            status=SessionStatus.ACTIVE,
            started_at=NOW,
        )
    )
    activities.add(
        Activity(
            id="activity_1",
            session_id="session_1",
            type=ActivityType.EXERCISE,
            sequence=1,
            concept_ids=["window_functions"],
            status=ActivityStatus.ACTIVE,
        )
    )
    provider = MockProvider()

    with pytest.raises(ActivityNotAnAssessmentError):
        _service(engine, provider).get_assessment("activity_1")
