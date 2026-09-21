from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import EvaluatorResponse
from app.ai.orchestrator import AIOrchestrator
from app.domain.entities import Activity, Concept, LearningGoal, Project, Session
from app.domain.enums import (
    ActivityStatus,
    ActivityType,
    ConceptStatus,
    GoalStatus,
    ProjectStatus,
    SessionMode,
    SessionStatus,
    TargetLevel,
)
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import (
    SqlActivityRepository,
    SqlConceptRepository,
    SqlEvidenceRepository,
    SqlGoalRepository,
    SqlProjectRepository,
    SqlReviewRepository,
    SqlSessionRepository,
)
from app.services.mastery_engine import MasteryEngine
from app.services.mastery_update_service import MasteryUpdateService
from app.services.project_evaluation_service import ProjectEvaluationService
from app.services.project_flow_service import ProjectFlowService
from app.services.project_submission_service import (
    NotAProjectTaskError,
    ProjectSubmissionService,
)
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


def _seed(engine: Engine) -> None:
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
    SqlProjectRepository(engine).add(
        Project(
            id="project_1",
            goal_id="goal_1",
            title="Build a small ETL pipeline",
            objective="Rank top products per warehouse using window functions.",
            difficulty=3,
            status=ProjectStatus.ACTIVE,
            concept_ids=["window_functions"],
            success_criteria=["Uses at least one window function"],
        )
    )
    SqlSessionRepository(engine).add(
        Session(
            id="session_1",
            goal_id="goal_1",
            mode=SessionMode.PROJECT,
            objective="Build a small ETL pipeline",
            status=SessionStatus.ACTIVE,
            started_at=NOW,
        )
    )
    SqlActivityRepository(engine).add(
        Activity(
            id="task_1",
            session_id="session_1",
            type=ActivityType.PROJECT_TASK,
            sequence=1,
            concept_ids=["window_functions"],
            status=ActivityStatus.PENDING,
        )
    )


def _service(engine: Engine, provider: object) -> ProjectFlowService:
    projects = SqlProjectRepository(engine)
    activities = SqlActivityRepository(engine)
    evidence = SqlEvidenceRepository(engine)
    concepts = SqlConceptRepository(engine)
    reviews = SqlReviewRepository(engine)
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    ids = FakeIdGenerator()

    submission = ProjectSubmissionService(projects, activities, evidence, FakeClock(), ids)
    evaluation = ProjectEvaluationService(projects, evidence, orchestrator, FakeClock(), ids)
    mastery_update = MasteryUpdateService(concepts, MasteryEngine(evidence))
    review_creation = ReviewCreationService(reviews, ReviewScheduler(FakeClock(), ids))

    return ProjectFlowService(submission, evaluation, mastery_update, review_creation)


def _evaluator_response(**overrides: object) -> EvaluatorResponse:
    defaults: dict[str, object] = dict(
        correctness=0.9,
        reasoning=0.8,
        completeness=0.85,
        independence=0.7,
        transfer=0.75,
        feedback="Solid application to a new dataset.",
        recommended_action="advance",
    )
    defaults.update(overrides)
    return EvaluatorResponse(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_submit_task_marks_task_completed(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed(engine)
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _evaluator_response())
    service = _service(engine, provider)

    result = await service.submit_task("project_1", "task_1", "goal_1", "https://github.com/x/y")

    assert result.task.status == ActivityStatus.COMPLETED
    stored = SqlActivityRepository(engine).get("task_1")
    assert stored is not None
    assert stored.status == ActivityStatus.COMPLETED


@pytest.mark.asyncio
async def test_submit_task_creates_submission_and_evaluation_evidence(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed(engine)
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _evaluator_response())
    service = _service(engine, provider)

    result = await service.submit_task("project_1", "task_1", "goal_1", "https://github.com/x/y")

    assert len(result.submission_evidence) == 1
    assert result.submission_evidence[0].correctness is None
    assert len(result.evaluation_evidence) == 1
    assert result.evaluation_evidence[0].correctness == 0.9


@pytest.mark.asyncio
async def test_submit_task_updates_mastery_and_schedules_review(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed(engine)
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _evaluator_response())
    service = _service(engine, provider)

    result = await service.submit_task("project_1", "task_1", "goal_1", "https://github.com/x/y")

    assert len(result.concepts) == 1
    assert result.concepts[0].id == "window_functions"
    assert result.concepts[0].mastery > 0
    reviews = SqlReviewRepository(engine).list_by_concept("window_functions")
    assert len(reviews) == 1


@pytest.mark.asyncio
async def test_submit_task_raises_when_task_is_not_a_project_task(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed(engine)
    SqlActivityRepository(engine).update(
        Activity(
            id="task_1",
            session_id="session_1",
            type=ActivityType.EXERCISE,
            sequence=1,
            concept_ids=["window_functions"],
            status=ActivityStatus.PENDING,
        )
    )
    provider = MockProvider()
    service = _service(engine, provider)

    with pytest.raises(NotAProjectTaskError):
        await service.submit_task("project_1", "task_1", "goal_1", "x")
