import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import EvaluatorResponse, ExerciseGeneratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.api.dependencies import get_project_flow_service, get_project_session_service
from app.domain.entities import Concept, LearningGoal
from app.domain.enums import ConceptStatus, ExerciseType, GoalStatus, TargetLevel
from app.main import app
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
    SqlReviewRepository,
    SqlSessionRepository,
)
from app.services.context_builder import ContextBuilder
from app.services.mastery_engine import MasteryEngine
from app.services.mastery_update_service import MasteryUpdateService
from app.services.project_evaluation_service import ProjectEvaluationService
from app.services.project_flow_service import ProjectFlowService
from app.services.project_generation_service import ProjectGenerationService
from app.services.project_session_service import ProjectSessionService
from app.services.project_submission_service import ProjectSubmissionService
from app.services.project_task_service import ProjectTaskService
from app.services.review_creation_service import ReviewCreationService
from app.services.review_scheduler import ReviewScheduler

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class UuidIdGenerator:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}"


def _generator_response(**overrides: object) -> ExerciseGeneratorResponse:
    defaults: dict[str, object] = dict(
        type=ExerciseType.DESIGN,
        difficulty=3,
        prompt="Build a small ETL pipeline that ranks top products.",
        success_criteria=["Uses at least one window function", "Handles duplicate rows"],
        hints=[],
        solution="",
        common_mistakes=[],
        transfer_variant=None,
    )
    defaults.update(overrides)
    return ExerciseGeneratorResponse(**defaults)  # type: ignore[arg-type]


def _evaluator_response(**overrides: object) -> EvaluatorResponse:
    defaults: dict[str, object] = dict(
        correctness=0.9,
        reasoning=0.8,
        completeness=0.85,
        independence=0.7,
        transfer=0.75,
        misconceptions=[],
        feedback="Solid application to a new dataset.",
        recommended_action="advance",
    )
    defaults.update(overrides)
    return EvaluatorResponse(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(engine: Engine) -> TestClient:
    provider = MockProvider()
    provider.set_response(ExerciseGeneratorResponse, _generator_response())
    provider.set_response(EvaluatorResponse, _evaluator_response())
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]

    goals = SqlGoalRepository(engine)
    concepts = SqlConceptRepository(engine)
    concept_relations = SqlConceptRelationRepository(engine)
    evidence = SqlEvidenceRepository(engine)
    mistakes = SqlMistakeRepository(engine)
    sessions = SqlSessionRepository(engine)
    activities = SqlActivityRepository(engine)
    projects = SqlProjectRepository(engine)
    reviews = SqlReviewRepository(engine)

    context_builder = ContextBuilder(
        goals=goals,
        concepts=concepts,
        concept_relations=concept_relations,
        evidence=evidence,
        mistakes=mistakes,
    )
    generation = ProjectGenerationService(
        goals=goals,
        context_builder=context_builder,
        projects=projects,
        orchestrator=orchestrator,
        clock=FakeClock(),
        ids=UuidIdGenerator(),
    )
    tasks = ProjectTaskService(
        projects=projects,
        sessions=sessions,
        activities=activities,
        clock=FakeClock(),
        ids=UuidIdGenerator(),
    )
    project_session = ProjectSessionService(
        goals=goals, projects=projects, generation=generation, tasks=tasks
    )
    submission = ProjectSubmissionService(
        projects, activities, evidence, FakeClock(), UuidIdGenerator()
    )
    evaluation = ProjectEvaluationService(
        projects, evidence, orchestrator, FakeClock(), UuidIdGenerator()
    )
    mastery_update = MasteryUpdateService(concepts, MasteryEngine(evidence))
    review_creation = ReviewCreationService(
        reviews, ReviewScheduler(FakeClock(), UuidIdGenerator())
    )
    project_flow = ProjectFlowService(submission, evaluation, mastery_update, review_creation)

    app.dependency_overrides[get_project_session_service] = lambda: project_session
    app.dependency_overrides[get_project_flow_service] = lambda: project_flow

    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


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


def test_create_project_returns_project_and_tasks(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)

    response = client.post(
        "/api/v1/goals/goal_1/projects", json={"concept_ids": ["window_functions"]}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["project"]["goal_id"] == "goal_1"
    assert body["project"]["status"] == "active"
    assert len(body["tasks"]) == 2
    assert body["tasks"][0]["description"] == "Uses at least one window function"


def test_create_project_404s_when_goal_missing(client: TestClient) -> None:
    response = client.post(
        "/api/v1/goals/missing/projects", json={"concept_ids": ["window_functions"]}
    )

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_list_projects_returns_created_projects(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    client.post("/api/v1/goals/goal_1/projects", json={"concept_ids": ["window_functions"]})

    response = client.get("/api/v1/goals/goal_1/projects")

    assert response.status_code == 200
    assert len(response.json()["projects"]) == 1


def test_get_project_404s_when_missing(client: TestClient) -> None:
    response = client.get("/api/v1/projects/missing")

    assert response.status_code == 404


def test_full_project_flow(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    created = client.post(
        "/api/v1/goals/goal_1/projects", json={"concept_ids": ["window_functions"]}
    ).json()
    project_id = created["project"]["id"]
    task_id = created["tasks"][0]["task_id"]

    get_response = client.get(f"/api/v1/projects/{project_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == project_id

    submit_response = client.post(
        f"/api/v1/projects/{project_id}/tasks/{task_id}/submit",
        json={"deliverable": "https://github.com/x/y"},
    )
    assert submit_response.status_code == 200
    submit_body = submit_response.json()
    assert submit_body["task_status"] == "completed"
    assert submit_body["evaluation"]["correctness"] == 0.9
    assert len(submit_body["updated_concepts"]) == 1
    assert submit_body["updated_concepts"][0]["concept_id"] == "window_functions"


def test_submit_task_missing_project_404s(client: TestClient) -> None:
    response = client.post(
        "/api/v1/projects/missing/tasks/task_1/submit", json={"deliverable": "x"}
    )

    assert response.status_code == 404


def test_submit_task_missing_task_404s(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    created = client.post(
        "/api/v1/goals/goal_1/projects", json={"concept_ids": ["window_functions"]}
    ).json()
    project_id = created["project"]["id"]

    response = client.post(
        f"/api/v1/projects/{project_id}/tasks/missing/submit", json={"deliverable": "x"}
    )

    assert response.status_code == 404
