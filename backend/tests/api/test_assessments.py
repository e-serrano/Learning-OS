import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import EvaluatorResponse, ExerciseGeneratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.api.dependencies import (
    get_assessment_completion_service,
    get_assessment_session_service,
    get_session_service,
)
from app.domain.entities import Concept, LearningGoal
from app.domain.enums import ConceptStatus, ExerciseType, GoalStatus, TargetLevel
from app.main import app
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
    SqlSessionRepository,
)
from app.services.answer_submission_service import AnswerSubmissionService
from app.services.assessment_completion_service import AssessmentCompletionService
from app.services.assessment_session_service import AssessmentSessionService
from app.services.context_builder import ContextBuilder
from app.services.evaluator_service import EvaluatorService
from app.services.evidence_creation_service import EvidenceCreationService
from app.services.session_service import SessionApplicationService
from app.services.transfer_assessment_service import TransferAssessmentService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class UuidIdGenerator:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}"


def _exercise_response(**overrides: object) -> ExerciseGeneratorResponse:
    defaults: dict[str, object] = dict(
        type=ExerciseType.SCENARIO,
        difficulty=3,
        prompt="Apply window functions to a new dataset.",
        success_criteria=["Uses RANK() correctly"],
        hints=["Think about ties"],
        solution="SELECT RANK() OVER (...) FROM shipments;",
        common_mistakes=["forgetting PARTITION BY"],
        transfer_variant="new-domain",
    )
    defaults.update(overrides)
    return ExerciseGeneratorResponse(**defaults)  # type: ignore[arg-type]


def _evaluator_response(**overrides: object) -> EvaluatorResponse:
    defaults: dict[str, object] = dict(
        correctness=0.9,
        reasoning=0.8,
        completeness=0.85,
        independence=0.7,
        transfer=0.8,
        misconceptions=[],
        feedback="Transferred the concept well.",
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
    provider.set_response(ExerciseGeneratorResponse, _exercise_response())
    provider.set_response(EvaluatorResponse, _evaluator_response())
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

    context_builder = ContextBuilder(
        goals=goals,
        concepts=concepts,
        concept_relations=concept_relations,
        evidence=evidence,
        mistakes=mistakes,
    )
    transfer_assessment = TransferAssessmentService(
        goals=goals,
        context_builder=context_builder,
        exercises=exercises,
        orchestrator=orchestrator,
        clock=FakeClock(),
        ids=UuidIdGenerator(),
    )
    assessment_session = AssessmentSessionService(
        sessions=sessions,
        activities=activities,
        exercises=exercises,
        transfer_assessment=transfer_assessment,
        clock=FakeClock(),
        ids=UuidIdGenerator(),
    )
    answer_submission = AnswerSubmissionService(
        exercises, sessions, attempts, FakeClock(), UuidIdGenerator()
    )
    evaluator = EvaluatorService(
        attempts, exercises, evaluations, orchestrator, FakeClock(), UuidIdGenerator()
    )
    evidence_creation = EvidenceCreationService(
        evaluations, attempts, exercises, evidence, FakeClock(), UuidIdGenerator()
    )
    assessment_completion = AssessmentCompletionService(
        answer_submission, evaluator, evidence_creation
    )
    session_service = SessionApplicationService(goals, sessions, FakeClock(), UuidIdGenerator())

    app.dependency_overrides[get_assessment_session_service] = lambda: assessment_session
    app.dependency_overrides[get_assessment_completion_service] = lambda: assessment_completion
    app.dependency_overrides[get_session_service] = lambda: session_service

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
    concepts = SqlConceptRepository(engine)
    concepts.add(
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
    concepts.link_to_goal("goal_1", "window_functions")


def test_create_assessment_returns_exercise_without_solution(
    client: TestClient, engine: Engine
) -> None:
    _seed_goal_and_concept(engine)

    response = client.post(
        "/api/v1/goals/goal_1/assessments", json={"concept_id": "window_functions"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["goal_id"] == "goal_1"
    assert body["concept_id"] == "window_functions"
    assert body["status"] == "active"
    assert body["exercise"]["prompt"] == "Apply window functions to a new dataset."
    assert "solution" not in body["exercise"]


def test_create_assessment_404s_when_goal_missing(client: TestClient) -> None:
    response = client.post(
        "/api/v1/goals/missing/assessments", json={"concept_id": "window_functions"}
    )

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_get_assessment_404s_when_missing(client: TestClient) -> None:
    response = client.get("/api/v1/assessments/missing")

    assert response.status_code == 404


def test_full_assessment_flow(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    created = client.post(
        "/api/v1/goals/goal_1/assessments", json={"concept_id": "window_functions"}
    ).json()
    assessment_id = created["assessment_id"]

    get_response = client.get(f"/api/v1/assessments/{assessment_id}")
    assert get_response.status_code == 200
    assert get_response.json()["assessment_id"] == assessment_id

    answer_response = client.post(
        f"/api/v1/assessments/{assessment_id}/answer",
        json={"answer": "SELECT RANK() OVER (...) FROM shipments;", "confidence": 80},
    )
    assert answer_response.status_code == 200
    answer_body = answer_response.json()
    assert answer_body["evaluation"]["correctness"] == 0.9
    assert answer_body["transfer_demonstrated"] is True
    assert answer_body["independence_demonstrated"] is True

    complete_response = client.post(f"/api/v1/assessments/{assessment_id}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"


def test_complete_assessment_twice_conflicts(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    created = client.post(
        "/api/v1/goals/goal_1/assessments", json={"concept_id": "window_functions"}
    ).json()
    assessment_id = created["assessment_id"]
    client.post(f"/api/v1/assessments/{assessment_id}/complete")

    response = client.post(f"/api/v1/assessments/{assessment_id}/complete")

    assert response.status_code == 409
    assert response.json()["detail"]["error"]["code"] == "SESSION_STATE_ERROR"


def test_answer_missing_assessment_404s(client: TestClient) -> None:
    response = client.post(
        "/api/v1/assessments/missing/answer", json={"answer": "x", "confidence": 50}
    )

    assert response.status_code == 404
