from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_knowledge_explorer_service
from app.domain.entities import Concept, ConceptRelation, LearningGoal
from app.domain.enums import ConceptRelationType, ConceptStatus, TargetLevel
from app.main import app
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories.concept import SqlConceptRepository
from app.persistence.repositories.concept_relation import SqlConceptRelationRepository
from app.persistence.repositories.goal import SqlGoalRepository
from app.services.knowledge_explorer_service import KnowledgeExplorerService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def repos(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return (
        SqlGoalRepository(engine),
        SqlConceptRepository(engine),
        SqlConceptRelationRepository(engine),
    )


@pytest.fixture
def client(repos) -> TestClient:  # type: ignore[no-untyped-def]
    goals, concepts, relations = repos
    service = KnowledgeExplorerService(goals, concepts, relations)
    app.dependency_overrides[get_knowledge_explorer_service] = lambda: service
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def _seed_goal(goals: SqlGoalRepository, goal_id: str = "goal_1") -> None:
    goals.add(
        LearningGoal(
            id=goal_id,
            title="Learn BigQuery",
            target_level=TargetLevel.PROFESSIONAL,
            status="active",  # type: ignore[arg-type]
            priority=3,
            created_at=NOW,
            updated_at=NOW,
        )
    )


def _seed_concept(concepts: SqlConceptRepository, **overrides: object) -> Concept:
    defaults: dict[str, object] = dict(
        id="concept_1",
        title="Window functions",
        domain="sql",
        status=ConceptStatus.LEARNING,
        mastery=1.0,
        confidence=50.0,
        importance=3,
        retention=50.0,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    concept = Concept(**defaults)  # type: ignore[arg-type]
    concepts.add(concept)
    concepts.link_to_goal("goal_1", concept.id)
    return concept


def test_list_knowledge_returns_concepts(client: TestClient, repos) -> None:  # type: ignore[no-untyped-def]
    goals, concepts, _ = repos
    _seed_goal(goals)
    _seed_concept(concepts, id="c1")
    _seed_concept(concepts, id="c2")

    response = client.get("/api/v1/goals/goal_1/knowledge")

    assert response.status_code == 200
    ids = {c["id"] for c in response.json()["concepts"]}
    assert ids == {"c1", "c2"}


def test_list_knowledge_404s_when_goal_missing(client: TestClient) -> None:
    response = client.get("/api/v1/goals/missing/knowledge")

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_list_knowledge_filters_by_status(client: TestClient, repos) -> None:  # type: ignore[no-untyped-def]
    goals, concepts, _ = repos
    _seed_goal(goals)
    _seed_concept(concepts, id="c1", status=ConceptStatus.MASTERED)
    _seed_concept(concepts, id="c2", status=ConceptStatus.LEARNING)

    response = client.get("/api/v1/goals/goal_1/knowledge", params={"status": "mastered"})

    ids = {c["id"] for c in response.json()["concepts"]}
    assert ids == {"c1"}


def test_list_knowledge_filters_by_mastery_lt(client: TestClient, repos) -> None:  # type: ignore[no-untyped-def]
    goals, concepts, _ = repos
    _seed_goal(goals)
    _seed_concept(concepts, id="c1", mastery=1.0)
    _seed_concept(concepts, id="c2", mastery=4.0)

    response = client.get("/api/v1/goals/goal_1/knowledge", params={"mastery_lt": 2.0})

    ids = {c["id"] for c in response.json()["concepts"]}
    assert ids == {"c1"}


def test_get_concept_returns_it(client: TestClient, repos) -> None:  # type: ignore[no-untyped-def]
    goals, concepts, _ = repos
    _seed_goal(goals)
    _seed_concept(concepts, id="c1")

    response = client.get("/api/v1/concepts/c1")

    assert response.status_code == 200
    assert response.json()["id"] == "c1"


def test_get_concept_404s_when_missing(client: TestClient) -> None:
    response = client.get("/api/v1/concepts/missing")

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_list_concept_relations(client: TestClient, repos) -> None:  # type: ignore[no-untyped-def]
    goals, concepts, relations = repos
    _seed_goal(goals)
    _seed_concept(concepts, id="c1")
    _seed_concept(concepts, id="c2")
    relations.add(
        ConceptRelation(source_id="c1", target_id="c2", relation=ConceptRelationType.RELATED_TO)
    )

    response = client.get("/api/v1/concepts/c1/relations")

    assert response.status_code == 200
    body = response.json()["relations"]
    assert len(body) == 1
    assert body[0]["target_id"] == "c2"


def test_list_concept_relations_404s_when_concept_missing(client: TestClient) -> None:
    response = client.get("/api/v1/concepts/missing/relations")

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"
