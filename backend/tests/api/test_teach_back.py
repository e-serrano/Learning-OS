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
    get_activity_content_service,
    get_adaptive_activity_service,
    get_answer_flow_service,
    get_next_activity_service,
    get_session_service,
    get_teach_back_session_service,
)
from app.domain.entities import Concept, LearningGoal
from app.domain.enums import (
    ConceptStatus,
    EvidenceSourceType,
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
from app.services.teach_back_service import TeachBackService
from app.services.teach_back_session_service import TeachBackSessionService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class UuidIdGenerator:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}"


def _exercise_response(**overrides: object) -> ExerciseGeneratorResponse:
    defaults: dict[str, object] = dict(
        type=ExerciseType.MCQ,  # deliberately NOT teach_back -- the app must force it anyway
        difficulty=2,
        prompt="Explain window functions as if teaching a beginner.",
        success_criteria=["Covers the OVER clause"],
        hints=[],
        solution="A model explanation.",
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
        feedback="Good explanation.",
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
    reviews = SqlReviewRepository(engine)

    context_builder = ContextBuilder(
        goals=goals,
        concepts=concepts,
        concept_relations=concept_relations,
        evidence=evidence,
        mistakes=mistakes,
    )
    teach_back = TeachBackService(
        goals=goals,
        context_builder=context_builder,
        exercises=exercises,
        orchestrator=orchestrator,
        clock=FakeClock(),
        ids=UuidIdGenerator(),
    )
    teach_back_session = TeachBackSessionService(
        sessions=sessions,
        activities=activities,
        exercises=exercises,
        teach_back=teach_back,
        clock=FakeClock(),
        ids=UuidIdGenerator(),
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

    app.dependency_overrides[get_teach_back_session_service] = lambda: teach_back_session
    app.dependency_overrides[get_session_service] = lambda: session_service
    app.dependency_overrides[get_next_activity_service] = lambda: next_activity_service
    app.dependency_overrides[get_adaptive_activity_service] = lambda: adaptive_activity
    app.dependency_overrides[get_activity_content_service] = lambda: activity_content
    app.dependency_overrides[get_answer_flow_service] = lambda: answer_flow

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


def test_create_teach_back_forces_the_teach_back_exercise_type(
    client: TestClient, engine: Engine
) -> None:
    _seed_goal_and_concept(engine)

    response = client.post(
        "/api/v1/goals/goal_1/teach-back", json={"concept_id": "window_functions"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["goal_id"] == "goal_1"
    assert body["concept_id"] == "window_functions"
    assert body["status"] == "active"
    assert body["exercise"]["type"] == "teach_back"
    assert "solution" not in body["exercise"]


def test_create_teach_back_404s_when_goal_missing(client: TestClient) -> None:
    response = client.post(
        "/api/v1/goals/missing/teach-back", json={"concept_id": "window_functions"}
    )

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_get_teach_back_404s_when_missing(client: TestClient) -> None:
    response = client.get("/api/v1/teach-back/missing")

    assert response.status_code == 404


def test_full_teach_back_flow_tags_evidence_with_the_teach_back_source_type(
    client: TestClient, engine: Engine
) -> None:
    _seed_goal_and_concept(engine)
    created = client.post(
        "/api/v1/goals/goal_1/teach-back", json={"concept_id": "window_functions"}
    ).json()
    teach_back_id = created["teach_back_id"]
    session_id = created["session_id"]

    get_response = client.get(f"/api/v1/teach-back/{teach_back_id}")
    assert get_response.status_code == 200
    assert get_response.json()["teach_back_id"] == teach_back_id

    answer_response = client.post(
        f"/api/v1/sessions/{session_id}/activities/{teach_back_id}/answer",
        json={
            "answer": "A window function computes a value across a set of rows.",
            "confidence": 80,
        },
    )
    assert answer_response.status_code == 200
    answer_body = answer_response.json()
    assert answer_body["evaluation"]["correctness"] == 0.9
    assert len(answer_body["knowledge_updates"]) == 1
    assert answer_body["knowledge_updates"][0]["concept_id"] == "window_functions"

    stored_evidence = SqlEvidenceRepository(engine).list_by_goal("goal_1")
    assert len(stored_evidence) == 1
    assert stored_evidence[0].source_type == EvidenceSourceType.TEACH_BACK

    complete_response = client.post(f"/api/v1/sessions/{session_id}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"
