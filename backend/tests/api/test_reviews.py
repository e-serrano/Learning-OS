from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.api.dependencies import get_review_flow_service, get_todays_reviews_service
from app.domain.entities import Concept, LearningGoal, Review
from app.domain.enums import ConceptStatus, GoalStatus, ReviewStatus, TargetLevel
from app.main import app
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import (
    SqlActivityRepository,
    SqlConceptRepository,
    SqlEvidenceRepository,
    SqlGoalRepository,
    SqlReviewRepository,
    SqlSessionRepository,
)
from app.services.mastery_engine import MasteryEngine
from app.services.mastery_update_service import MasteryUpdateService
from app.services.retention_update_service import RetentionUpdateService
from app.services.review_completion_service import ReviewCompletionService
from app.services.review_creation_service import ReviewCreationService
from app.services.review_flow_service import ReviewFlowService
from app.services.review_scheduler import ReviewScheduler
from app.services.todays_reviews_service import TodaysReviewsService

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


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(engine: Engine) -> TestClient:
    reviews = SqlReviewRepository(engine)
    sessions = SqlSessionRepository(engine)
    activities = SqlActivityRepository(engine)
    evidence = SqlEvidenceRepository(engine)
    concepts = SqlConceptRepository(engine)

    todays_reviews = TodaysReviewsService(reviews, FakeClock())
    review_creation = ReviewCreationService(
        reviews, ReviewScheduler(FakeClock(), FakeIdGenerator())
    )
    review_completion = ReviewCompletionService(
        reviews, evidence, review_creation, FakeClock(), FakeIdGenerator()
    )
    mastery_update = MasteryUpdateService(concepts, MasteryEngine(evidence))
    retention_update = RetentionUpdateService(concepts, evidence)
    review_flow = ReviewFlowService(
        reviews=reviews,
        sessions=sessions,
        activities=activities,
        review_completion=review_completion,
        mastery_update=mastery_update,
        retention_update=retention_update,
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )

    app.dependency_overrides[get_todays_reviews_service] = lambda: todays_reviews
    app.dependency_overrides[get_review_flow_service] = lambda: review_flow
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


def _seed_review(engine: Engine, **overrides: object) -> Review:
    defaults: dict[str, object] = dict(
        id="review_seed",
        concept_id="window_functions",
        goal_id="goal_1",
        scheduled_at=NOW - timedelta(hours=1),
        interval_days=4.0,
        status=ReviewStatus.SCHEDULED,
    )
    defaults.update(overrides)
    review = Review(**defaults)  # type: ignore[arg-type]
    SqlReviewRepository(engine).add(review)
    return review


def test_list_todays_reviews_returns_due_ones(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    _seed_review(engine)

    response = client.get("/api/v1/reviews/today")

    assert response.status_code == 200
    ids = {r["id"] for r in response.json()["reviews"]}
    assert ids == {"review_seed"}


def test_list_todays_reviews_excludes_completed(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)
    _seed_review(engine, status=ReviewStatus.COMPLETED, completed_at=NOW)

    response = client.get("/api/v1/reviews/today")

    assert response.json()["reviews"] == []


def test_complete_review_returns_next_review_and_concept(
    client: TestClient, engine: Engine
) -> None:
    _seed_goal_and_concept(engine)
    _seed_review(engine)

    response = client.post(
        "/api/v1/reviews/review_seed/complete", json={"answer": "ROW_NUMBER", "confidence": 90}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["completed_review"]["status"] == "completed"
    assert body["next_review"]["id"] != "review_seed"
    assert body["concept"]["concept_id"] == "window_functions"
    assert body["concept"]["retention"] == 90.0


def test_complete_review_404s_when_missing(client: TestClient) -> None:
    response = client.post(
        "/api/v1/reviews/missing/complete", json={"answer": "x", "confidence": 50}
    )

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_complete_review_conflicts_when_already_completed(
    client: TestClient, engine: Engine
) -> None:
    _seed_goal_and_concept(engine)
    _seed_review(engine, status=ReviewStatus.COMPLETED, completed_at=NOW)

    response = client.post(
        "/api/v1/reviews/review_seed/complete", json={"answer": "x", "confidence": 50}
    )

    assert response.status_code == 409
    assert response.json()["detail"]["error"]["code"] == "SESSION_STATE_ERROR"
