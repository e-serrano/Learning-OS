from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_goal_service
from app.domain.entities import LearningGoal
from app.domain.enums import GoalStatus, TargetLevel
from app.main import app
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories.goal import SqlGoalRepository
from app.services.goal_service import GoalApplicationService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class SequentialIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


@pytest.fixture
def repo(tmp_path: Path) -> SqlGoalRepository:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return SqlGoalRepository(engine)


@pytest.fixture
def client(repo: SqlGoalRepository) -> TestClient:
    service = GoalApplicationService(repo, FixedClock(), SequentialIdGenerator())
    app.dependency_overrides[get_goal_service] = lambda: service
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def _seed_active_goal(repo: SqlGoalRepository, goal_id: str = "goal_1") -> LearningGoal:
    goal = LearningGoal(
        id=goal_id,
        title="Learn BigQuery",
        target_level=TargetLevel.PROFESSIONAL,
        status=GoalStatus.ACTIVE,
        priority=3,
        created_at=NOW,
        updated_at=NOW,
    )
    repo.add(goal)
    return goal


def test_create_goal_returns_it_as_draft(client: TestClient) -> None:
    response = client.post(
        "/api/v1/goals",
        json={"title": "Learn BigQuery", "target_level": "professional"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["title"] == "Learn BigQuery"
    assert body["id"] == "goal_1"


def test_create_goal_rejects_blank_title(client: TestClient) -> None:
    response = client.post("/api/v1/goals", json={"title": "   ", "target_level": "professional"})

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "VALIDATION_ERROR"


def test_list_goals_returns_created_goals(client: TestClient, repo: SqlGoalRepository) -> None:
    _seed_active_goal(repo, "goal_1")
    _seed_active_goal(repo, "goal_2")

    response = client.get("/api/v1/goals")

    assert response.status_code == 200
    ids = {g["id"] for g in response.json()["goals"]}
    assert ids == {"goal_1", "goal_2"}


def test_get_goal_returns_it(client: TestClient, repo: SqlGoalRepository) -> None:
    _seed_active_goal(repo)

    response = client.get("/api/v1/goals/goal_1")

    assert response.status_code == 200
    assert response.json()["id"] == "goal_1"


def test_get_goal_404_when_missing(client: TestClient) -> None:
    response = client.get("/api/v1/goals/missing")

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_pause_active_goal(client: TestClient, repo: SqlGoalRepository) -> None:
    _seed_active_goal(repo)

    response = client.post("/api/v1/goals/goal_1/pause")

    assert response.status_code == 200
    assert response.json()["status"] == "paused"


def test_pause_draft_goal_is_a_conflict(client: TestClient) -> None:
    client.post("/api/v1/goals", json={"title": "Learn BigQuery", "target_level": "professional"})

    response = client.post("/api/v1/goals/goal_1/pause")

    assert response.status_code == 409
    assert response.json()["detail"]["error"]["code"] == "SESSION_STATE_ERROR"


def test_complete_active_goal(client: TestClient, repo: SqlGoalRepository) -> None:
    _seed_active_goal(repo)

    response = client.post("/api/v1/goals/goal_1/complete")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_pause_missing_goal_404s(client: TestClient) -> None:
    response = client.post("/api/v1/goals/missing/pause")

    assert response.status_code == 404
