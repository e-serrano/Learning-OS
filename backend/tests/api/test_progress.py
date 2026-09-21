from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.api.dependencies import get_progress_service
from app.domain.entities import Concept, LearningGoal
from app.domain.enums import ConceptStatus, GoalStatus, TargetLevel
from app.main import app
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import (
    SqlConceptRepository,
    SqlGoalRepository,
    SqlReviewRepository,
    SqlSessionRepository,
)
from app.services.progress_service import ProgressService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(engine: Engine) -> TestClient:
    service = ProgressService(
        goals=SqlGoalRepository(engine),
        concepts=SqlConceptRepository(engine),
        reviews=SqlReviewRepository(engine),
        sessions=SqlSessionRepository(engine),
        clock=FakeClock(),
    )
    app.dependency_overrides[get_progress_service] = lambda: service
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
            status=ConceptStatus.MASTERED,
            mastery=4.0,
            confidence=80,
            importance=3,
            retention=90,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    concepts.link_to_goal("goal_1", "window_functions")


def test_get_progress_returns_summary(client: TestClient, engine: Engine) -> None:
    _seed_goal_and_concept(engine)

    response = client.get("/api/v1/goals/goal_1/progress")

    assert response.status_code == 200
    body = response.json()
    assert body["concepts_total"] == 1
    assert body["mastered"] == 1
    assert body["mastery"] == 0.8


def test_get_progress_404s_when_goal_missing(client: TestClient) -> None:
    response = client.get("/api/v1/goals/missing/progress")

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"
