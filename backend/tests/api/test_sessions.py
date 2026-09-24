import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import EvaluatorResponse, ExerciseGeneratorResponse, TutorResponse
from app.ai.orchestrator import AIOrchestrator
from app.api.dependencies import (
    get_activity_content_service,
    get_adaptive_activity_service,
    get_answer_flow_service,
    get_next_activity_service,
    get_session_service,
    get_tutor_service,
)
from app.domain.entities import Activity, Concept, LearningGoal
from app.domain.enums import (
    ActivityStatus,
    ActivityType,
    ConceptStatus,
    ExerciseType,
    GoalStatus,
    TargetLevel,
)
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
    SqlReviewRepository,
    SqlSessionRepository,
)
from app.services.activity_content_service import ActivityContentService
from app.services.activity_selector import ActivitySelector
from app.services.adaptive_activity_service import AdaptiveActivityService
from app.services.answer_flow_service import AnswerFlowService
from app.services.answer_submission_service import AnswerSubmissionService
from app.services.context_builder import ContextBuilder
from app.services.evaluator_service import EvaluatorService
from app.services.evidence_creation_service import EvidenceCreationService
from app.services.exercise_generator_service import ExerciseGeneratorService
from app.services.mastery_engine import MasteryEngine
from app.services.mastery_update_service import MasteryUpdateService
from app.services.mistake_tracker import MistakeTracker
from app.services.mistake_update_service import MistakeUpdateService
from app.services.next_activity_service import NextActivityService
from app.services.review_creation_service import ReviewCreationService
from app.services.review_scheduler import ReviewScheduler
from app.services.session_service import SessionApplicationService
from app.services.tutor_service import TutorService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class UuidIdGenerator:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}"


def _exercise_response(**overrides: object) -> ExerciseGeneratorResponse:
    defaults: dict[str, object] = dict(
        type=ExerciseType.CODING,
        difficulty=3,
        prompt="Write a query using ROW_NUMBER().",
        success_criteria=["Uses ROW_NUMBER()"],
        hints=["Think about ordering"],
        solution="SELECT ROW_NUMBER() OVER (ORDER BY id) FROM t;",
        common_mistakes=["forgetting ORDER BY"],
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


def _tutor_response(**overrides: object) -> TutorResponse:
    defaults: dict[str, object] = dict(
        mode="question",
        content="What do you think happens if two rows share the same value?",
        check_for_understanding=None,
        next_activity=None,
    )
    defaults.update(overrides)
    return TutorResponse(**defaults)  # type: ignore[arg-type]


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
    provider.set_response(TutorResponse, _tutor_response())
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
        ids=UuidIdGenerator(),
    )
    activity_content = ActivityContentService(activities, exercise_generator)
    activity_selector = ActivitySelector(
        concepts, concept_relations, mistakes, evidence, FakeClock()
    )
    next_activity_service = NextActivityService(
        sessions, activities, activity_selector, UuidIdGenerator()
    )
    adaptive_activity = AdaptiveActivityService(
        sessions, activities, activity_selector, UuidIdGenerator()
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
    mistake_tracker = MistakeTracker(mistakes, FakeClock(), UuidIdGenerator())
    mistake_update = MistakeUpdateService(evaluations, attempts, exercises, mistake_tracker)
    mastery_engine = MasteryEngine(evidence)
    mastery_update = MasteryUpdateService(concepts, mastery_engine)
    review_scheduler = ReviewScheduler(FakeClock(), UuidIdGenerator())
    review_creation = ReviewCreationService(reviews, review_scheduler)
    answer_flow = AnswerFlowService(
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
    session_service = SessionApplicationService(goals, sessions, FakeClock(), UuidIdGenerator())
    tutor_service = TutorService(
        goals=goals, sessions=sessions, context_builder=context_builder, orchestrator=orchestrator
    )

    app.dependency_overrides[get_session_service] = lambda: session_service
    app.dependency_overrides[get_next_activity_service] = lambda: next_activity_service
    app.dependency_overrides[get_adaptive_activity_service] = lambda: adaptive_activity
    app.dependency_overrides[get_activity_content_service] = lambda: activity_content
    app.dependency_overrides[get_answer_flow_service] = lambda: answer_flow
    app.dependency_overrides[get_tutor_service] = lambda: tutor_service

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


def test_create_session_returns_active_session(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)

    response = client.post(
        "/api/v1/goals/goal_1/sessions", json={"mode": "guided", "duration_minutes": 30}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert body["goal_id"] == "goal_1"


def test_create_session_404s_when_goal_missing(client: TestClient) -> None:
    response = client.post(
        "/api/v1/goals/missing/sessions", json={"mode": "guided", "duration_minutes": 30}
    )

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_get_session_404s_when_missing(client: TestClient) -> None:
    response = client.get("/api/v1/sessions/missing")

    assert response.status_code == 404


def test_full_session_flow(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    session_id = client.post(
        "/api/v1/goals/goal_1/sessions", json={"mode": "guided", "duration_minutes": 30}
    ).json()["id"]

    next_response = client.post(f"/api/v1/sessions/{session_id}/next")
    assert next_response.status_code == 200
    next_body = next_response.json()
    assert next_body["type"] == "exercise"
    assert next_body["content"]["prompt"] == "Write a query using ROW_NUMBER()."
    assert "solution" not in next_body["content"]
    activity_id = next_body["activity_id"]

    answer_response = client.post(
        f"/api/v1/sessions/{session_id}/activities/{activity_id}/answer",
        json={"answer": "SELECT ROW_NUMBER() OVER (ORDER BY id) FROM t;", "confidence": 70},
    )
    assert answer_response.status_code == 200
    answer_body = answer_response.json()
    assert answer_body["evaluation"]["correctness"] == 0.9
    assert len(answer_body["knowledge_updates"]) == 1
    assert answer_body["knowledge_updates"][0]["concept_id"] == "window_functions"
    assert answer_body["next_activity"] is not None

    complete_response = client.post(f"/api/v1/sessions/{session_id}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"


def test_complete_session_twice_conflicts(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    session_id = client.post(
        "/api/v1/goals/goal_1/sessions", json={"mode": "guided", "duration_minutes": 30}
    ).json()["id"]
    client.post(f"/api/v1/sessions/{session_id}/complete")

    response = client.post(f"/api/v1/sessions/{session_id}/complete")

    assert response.status_code == 409
    assert response.json()["detail"]["error"]["code"] == "SESSION_STATE_ERROR"


def test_answer_before_next_conflicts(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    session_id = client.post(
        "/api/v1/goals/goal_1/sessions", json={"mode": "guided", "duration_minutes": 30}
    ).json()["id"]
    activities = SqlActivityRepository(engine)
    activities.add(
        Activity(
            id="activity_no_exercise",
            session_id=session_id,
            type=ActivityType.EXERCISE,
            sequence=1,
            concept_ids=["window_functions"],
            status=ActivityStatus.ACTIVE,
        )
    )

    response = client.post(
        f"/api/v1/sessions/{session_id}/activities/activity_no_exercise/answer",
        json={"answer": "x", "confidence": 50},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["error"]["code"] == "SESSION_STATE_ERROR"


def test_answer_missing_activity_404s(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    session_id = client.post(
        "/api/v1/goals/goal_1/sessions", json={"mode": "guided", "duration_minutes": 30}
    ).json()["id"]

    response = client.post(
        f"/api/v1/sessions/{session_id}/activities/missing/answer",
        json={"answer": "x", "confidence": 50},
    )

    assert response.status_code == 404


def test_tutor_turn_returns_a_socratic_response(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    session_id = client.post(
        "/api/v1/goals/goal_1/sessions", json={"mode": "socratic", "duration_minutes": 30}
    ).json()["id"]

    response = client.post(
        f"/api/v1/sessions/{session_id}/tutor",
        json={"concept_id": "window_functions", "message": "Is it like a subquery?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "question"
    assert "same value" in body["content"]


def test_tutor_turn_accepts_history(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    session_id = client.post(
        "/api/v1/goals/goal_1/sessions", json={"mode": "socratic", "duration_minutes": 30}
    ).json()["id"]

    response = client.post(
        f"/api/v1/sessions/{session_id}/tutor",
        json={
            "concept_id": "window_functions",
            "message": "Not sure.",
            "history": [
                {"speaker": "tutor", "content": "What have you tried so far?"},
                {"speaker": "learner", "content": "Nothing yet."},
            ],
        },
    )

    assert response.status_code == 200


def test_tutor_turn_returns_an_interview_response(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    session_id = client.post(
        "/api/v1/goals/goal_1/sessions", json={"mode": "interview", "duration_minutes": 30}
    ).json()["id"]

    response = client.post(
        f"/api/v1/sessions/{session_id}/tutor",
        json={"concept_id": "window_functions", "message": "I'd use a window function."},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "question"


def test_tutor_turn_rejects_a_non_tutorable_session(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    session_id = client.post(
        "/api/v1/goals/goal_1/sessions", json={"mode": "guided", "duration_minutes": 30}
    ).json()["id"]

    response = client.post(
        f"/api/v1/sessions/{session_id}/tutor", json={"concept_id": "window_functions"}
    )

    assert response.status_code == 409
    assert response.json()["detail"]["error"]["code"] == "SESSION_STATE_ERROR"


def test_tutor_turn_404s_when_session_missing(client: TestClient) -> None:
    response = client.post(
        "/api/v1/sessions/missing/tutor", json={"concept_id": "window_functions"}
    )

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_tutor_turn_404s_when_concept_missing(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    session_id = client.post(
        "/api/v1/goals/goal_1/sessions", json={"mode": "socratic", "duration_minutes": 30}
    ).json()["id"]

    response = client.post(
        f"/api/v1/sessions/{session_id}/tutor", json={"concept_id": "missing_concept"}
    )

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"
