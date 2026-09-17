import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import EvaluatorResponse, ExerciseGeneratorResponse
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
    SqlEvaluationRepository,
    SqlEvidenceRepository,
    SqlExerciseAttemptRepository,
    SqlExerciseRepository,
    SqlGoalRepository,
    SqlMistakeRepository,
    SqlReviewRepository,
    SqlSessionRepository,
)
from app.services.activity_content_service import ActivityContentService
from app.services.activity_selector import ActivitySelector
from app.services.adaptive_activity_service import AdaptiveActivityService
from app.services.answer_flow_service import (
    ActivityHasNoExerciseError,
    ActivityNotFoundError,
    AnswerFlowService,
)
from app.services.answer_submission_service import AnswerSubmissionService
from app.services.context_builder import ContextBuilder
from app.services.evaluator_service import EvaluatorService
from app.services.evidence_creation_service import EvidenceCreationService
from app.services.exercise_generator_service import ExerciseGeneratorService
from app.services.mastery_engine import MasteryEngine
from app.services.mastery_update_service import MasteryUpdateService
from app.services.mistake_tracker import MistakeTracker
from app.services.mistake_update_service import MistakeUpdateService
from app.services.next_activity_service import SessionNotFoundError
from app.services.review_creation_service import ReviewCreationService
from app.services.review_scheduler import ReviewScheduler

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class FakeIdGenerator:
    """Uuid-based rather than counter-based: this test wires up many
    services, each constructed with its own instance, and separately
    seeds an Exercise/Activity via a standalone helper before building
    the pipeline -- a shared counter across all of those would collide
    (two independently-numbered "first ids") the way a real per-process
    generator never would."""

    def new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}"


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


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


def _seed_session(engine: Engine, status: SessionStatus = SessionStatus.ACTIVE) -> None:
    SqlSessionRepository(engine).add(
        Session(
            id="session_1",
            goal_id="goal_1",
            mode=SessionMode.GUIDED,
            objective="Practice",
            status=status,
            started_at=NOW,
        )
    )


def _seed_activity(
    engine: Engine, concept_id: str = "window_functions", exercise_id: str | None = None
) -> Activity:
    activity = Activity(
        id="activity_seed",
        session_id="session_1",
        type=ActivityType.EXERCISE,
        sequence=1,
        concept_ids=[concept_id],
        status=ActivityStatus.ACTIVE,
        exercise_id=exercise_id,
    )
    SqlActivityRepository(engine).add(activity)
    return activity


def _service(engine: Engine, provider: object) -> AnswerFlowService:
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    goals = SqlGoalRepository(engine)
    concepts = SqlConceptRepository(engine)
    concept_relations = SqlConceptRelationRepository(engine)
    evidence = SqlEvidenceRepository(engine)
    mistakes = SqlMistakeRepository(engine)
    sessions = SqlSessionRepository(engine)
    activities = SqlActivityRepository(engine)
    exercises = SqlExerciseRepository(engine)
    attempts = SqlExerciseAttemptRepository(engine)
    evaluations = SqlEvaluationRepository(engine)
    reviews = SqlReviewRepository(engine)

    context_builder = ContextBuilder(
        goals=goals,
        concepts=concepts,
        concept_relations=concept_relations,
        evidence=evidence,
        mistakes=mistakes,
    )
    exercise_generator = ExerciseGeneratorService(
        goals=goals,
        context_builder=context_builder,
        exercises=exercises,
        orchestrator=orchestrator,
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )
    activity_content = ActivityContentService(activities, exercise_generator)
    answer_submission = AnswerSubmissionService(
        exercises, sessions, attempts, FakeClock(), FakeIdGenerator()
    )
    evaluator = EvaluatorService(
        attempts, exercises, evaluations, orchestrator, FakeClock(), FakeIdGenerator()
    )
    evidence_creation = EvidenceCreationService(
        evaluations, attempts, exercises, evidence, FakeClock(), FakeIdGenerator()
    )
    mistake_tracker = MistakeTracker(mistakes, FakeClock(), FakeIdGenerator())
    mistake_update = MistakeUpdateService(evaluations, attempts, exercises, mistake_tracker)
    mastery_engine = MasteryEngine(evidence)
    mastery_update = MasteryUpdateService(concepts, mastery_engine)
    review_scheduler = ReviewScheduler(FakeClock(), FakeIdGenerator())
    review_creation = ReviewCreationService(reviews, review_scheduler)
    activity_selector = ActivitySelector(
        concepts, concept_relations, mistakes, evidence, FakeClock()
    )
    adaptive_activity = AdaptiveActivityService(
        sessions, activities, activity_selector, FakeIdGenerator()
    )

    return AnswerFlowService(
        sessions=sessions,
        activities=activities,
        answer_submission=answer_submission,
        evaluator=evaluator,
        evidence_creation=evidence_creation,
        mistake_update=mistake_update,
        mastery_update=mastery_update,
        review_creation=review_creation,
        adaptive_activity=adaptive_activity,
        activity_content=activity_content,
    )


def _exercise_response(**overrides: object) -> ExerciseGeneratorResponse:
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


def _evaluator_response(**overrides: object) -> EvaluatorResponse:
    defaults: dict[str, object] = dict(
        correctness=0.9,
        reasoning=0.8,
        completeness=0.85,
        independence=0.7,
        transfer=0.6,
        misconceptions=[],
        feedback="Good job.",
        recommended_action="advance",
    )
    defaults.update(overrides)
    return EvaluatorResponse(**defaults)  # type: ignore[arg-type]


async def _seed_exercise(engine: Engine, provider: MockProvider, concept_id: str) -> str:
    """Generates and persists a real Exercise for `concept_id`, returning its id."""
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    goals = SqlGoalRepository(engine)
    context_builder = ContextBuilder(
        goals=goals,
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        mistakes=SqlMistakeRepository(engine),
    )
    generator = ExerciseGeneratorService(
        goals=goals,
        context_builder=context_builder,
        exercises=SqlExerciseRepository(engine),
        orchestrator=orchestrator,
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )
    exercise = await generator.generate("goal_1", concept_id)
    return exercise.id


@pytest.mark.asyncio
async def test_submit_answer_runs_the_full_pipeline(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    _seed_concept(engine, "window_functions")
    _seed_session(engine)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _exercise_response())
    exercise_id = await _seed_exercise(engine, provider, "window_functions")
    _seed_activity(engine, concept_id="window_functions", exercise_id=exercise_id)
    provider.set_response(EvaluatorResponse, _evaluator_response())

    result = await _service(engine, provider).submit_answer(
        "session_1",
        "activity_seed",
        "SELECT ROW_NUMBER() OVER (ORDER BY id) FROM t;",
        confidence=70,
    )

    assert result.evaluation.correctness == 0.9
    assert len(result.knowledge_updates) == 1
    update = result.knowledge_updates[0]
    assert update.concept_id == "window_functions"
    assert update.mistakes_recorded == 0
    assert result.next_activity is not None
    assert result.next_activity.exercise.concept_ids == ["window_functions"]

    completed_activity = SqlActivityRepository(engine).get("activity_seed")
    assert completed_activity is not None
    assert completed_activity.status == ActivityStatus.COMPLETED


@pytest.mark.asyncio
async def test_submit_answer_records_mistakes_from_misconceptions(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    _seed_concept(engine, "window_functions")
    _seed_session(engine)
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _exercise_response())
    exercise_id = await _seed_exercise(engine, provider, "window_functions")
    _seed_activity(engine, concept_id="window_functions", exercise_id=exercise_id)
    provider.set_response(
        EvaluatorResponse, _evaluator_response(misconceptions=["confused ROW_NUMBER with RANK"])
    )

    result = await _service(engine, provider).submit_answer(
        "session_1", "activity_seed", "wrong answer", confidence=40
    )

    assert result.knowledge_updates[0].mistakes_recorded == 1


@pytest.mark.asyncio
async def test_submit_answer_raises_when_session_missing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()

    with pytest.raises(SessionNotFoundError):
        await _service(engine, provider).submit_answer(
            "missing", "activity_seed", "answer", confidence=50
        )


@pytest.mark.asyncio
async def test_submit_answer_raises_when_activity_missing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    _seed_session(engine)
    provider = MockProvider()

    with pytest.raises(ActivityNotFoundError):
        await _service(engine, provider).submit_answer(
            "session_1", "missing", "answer", confidence=50
        )


@pytest.mark.asyncio
async def test_submit_answer_raises_when_activity_has_no_exercise(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    _seed_concept(engine, "window_functions")
    _seed_session(engine)
    _seed_activity(engine, exercise_id=None)
    provider = MockProvider()

    with pytest.raises(ActivityHasNoExerciseError):
        await _service(engine, provider).submit_answer(
            "session_1", "activity_seed", "answer", confidence=50
        )
