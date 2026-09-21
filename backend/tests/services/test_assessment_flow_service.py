from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import EvaluatorResponse
from app.ai.orchestrator import AIOrchestrator
from app.domain.entities import Activity, Concept, Exercise, LearningGoal, Session
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
    SqlConceptRepository,
    SqlEvaluationRepository,
    SqlEvidenceRepository,
    SqlExerciseAttemptRepository,
    SqlExerciseRepository,
    SqlGoalRepository,
    SqlReviewRepository,
    SqlSessionRepository,
)
from app.services.answer_submission_service import AnswerSubmissionService
from app.services.assessment_completion_service import AssessmentCompletionService
from app.services.assessment_flow_service import AssessmentFlowService
from app.services.evaluator_service import EvaluatorService
from app.services.evidence_creation_service import EvidenceCreationService
from app.services.mastery_engine import MasteryEngine
from app.services.mastery_update_service import MasteryUpdateService
from app.services.review_creation_service import ReviewCreationService
from app.services.review_scheduler import ReviewScheduler

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


def _seed_concept(engine: Engine) -> None:
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


def _seed_exercise_session_activity(engine: Engine) -> None:
    SqlExerciseRepository(engine).add(
        Exercise(
            id="exercise_1",
            type=ExerciseType.SCENARIO,
            difficulty=3,
            goal_id="goal_1",
            concept_ids=["window_functions"],
            prompt="Apply window functions to a new dataset.",
            solution="SELECT RANK() OVER (...) FROM shipments;",
            created_at=NOW,
        )
    )
    SqlSessionRepository(engine).add(
        Session(
            id="session_1",
            goal_id="goal_1",
            mode=SessionMode.ASSESSMENT,
            objective="Transfer assessment",
            status=SessionStatus.ACTIVE,
            started_at=NOW,
        )
    )
    SqlActivityRepository(engine).add(
        Activity(
            id="activity_1",
            session_id="session_1",
            type=ActivityType.ASSESSMENT,
            sequence=1,
            concept_ids=["window_functions"],
            status=ActivityStatus.ACTIVE,
            exercise_id="exercise_1",
        )
    )


def _service(engine: Engine, provider: object) -> AssessmentFlowService:
    exercises = SqlExerciseRepository(engine)
    sessions = SqlSessionRepository(engine)
    activities = SqlActivityRepository(engine)
    attempts = SqlExerciseAttemptRepository(engine)
    evaluations = SqlEvaluationRepository(engine)
    evidence = SqlEvidenceRepository(engine)
    concepts = SqlConceptRepository(engine)
    reviews = SqlReviewRepository(engine)
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]

    answer_submission = AnswerSubmissionService(
        exercises, sessions, attempts, FakeClock(), FakeIdGenerator()
    )
    evaluator = EvaluatorService(
        attempts, exercises, evaluations, orchestrator, FakeClock(), FakeIdGenerator()
    )
    evidence_creation = EvidenceCreationService(
        evaluations, attempts, exercises, evidence, FakeClock(), FakeIdGenerator()
    )
    completion = AssessmentCompletionService(answer_submission, evaluator, evidence_creation)
    mastery_update = MasteryUpdateService(concepts, MasteryEngine(evidence))
    review_creation = ReviewCreationService(
        reviews, ReviewScheduler(FakeClock(), FakeIdGenerator())
    )

    return AssessmentFlowService(
        activities=activities,
        completion=completion,
        mastery_update=mastery_update,
        review_creation=review_creation,
    )


def _evaluator_response(**overrides: object) -> EvaluatorResponse:
    defaults: dict[str, object] = dict(
        correctness=0.9,
        reasoning=0.8,
        completeness=0.7,
        independence=0.8,
        transfer=0.8,
        feedback="Transferred well.",
        recommended_action="advance",
    )
    defaults.update(overrides)
    return EvaluatorResponse(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_complete_assessment_marks_activity_completed(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_concept(engine)
    _seed_exercise_session_activity(engine)
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _evaluator_response())
    service = _service(engine, provider)

    result = await service.complete_assessment(
        "exercise_1", "session_1", "activity_1", "goal_1", "my answer", confidence=80
    )

    assert result.activity.status == ActivityStatus.COMPLETED
    stored = SqlActivityRepository(engine).get("activity_1")
    assert stored is not None
    assert stored.status == ActivityStatus.COMPLETED


@pytest.mark.asyncio
async def test_complete_assessment_updates_mastery(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_concept(engine)
    _seed_exercise_session_activity(engine)
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _evaluator_response())
    service = _service(engine, provider)

    result = await service.complete_assessment(
        "exercise_1", "session_1", "activity_1", "goal_1", "my answer", confidence=80
    )

    assert len(result.concepts) == 1
    assert result.concepts[0].id == "window_functions"
    assert result.concepts[0].mastery > 0
    stored = SqlConceptRepository(engine).get("window_functions")
    assert stored is not None
    assert stored.mastery == result.concepts[0].mastery


@pytest.mark.asyncio
async def test_complete_assessment_schedules_a_review(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_concept(engine)
    _seed_exercise_session_activity(engine)
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _evaluator_response())
    service = _service(engine, provider)

    await service.complete_assessment(
        "exercise_1", "session_1", "activity_1", "goal_1", "my answer", confidence=80
    )

    reviews = SqlReviewRepository(engine).list_by_concept("window_functions")
    assert len(reviews) == 1
