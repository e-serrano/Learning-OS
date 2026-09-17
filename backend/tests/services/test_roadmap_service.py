from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.domain.entities import Concept, LearningGoal
from app.domain.enums import (
    ConceptRelationType,
    ConceptStatus,
    GoalStatus,
    RoadmapStatus,
    TargetLevel,
)
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import (
    SqlConceptRelationRepository,
    SqlConceptRepository,
    SqlGoalRepository,
    SqlRoadmapRepository,
)
from app.services.context_builder import GoalNotFoundError
from app.services.roadmap_service import (
    RoadmapEdge,
    RoadmapNode,
    RoadmapNotFoundError,
    RoadmapService,
    RoadmapValidationError,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


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


def _seed_goal(engine: Engine, **overrides: object) -> None:
    defaults: dict[str, object] = dict(
        id="goal_1",
        title="Learn SQL",
        domain="sql",
        target_level=TargetLevel.PROFESSIONAL,
        status=GoalStatus.ACTIVE,
        priority=3,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    SqlGoalRepository(engine).add(LearningGoal(**defaults))  # type: ignore[arg-type]


def _service(engine: Engine) -> RoadmapService:
    return RoadmapService(
        goals=SqlGoalRepository(engine),
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        roadmaps=SqlRoadmapRepository(engine),
        clock=FakeClock(NOW),
        ids=FakeIdGenerator(),
    )


def test_build_roadmap_creates_concepts_links_and_relations(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    nodes = [
        RoadmapNode(id="select_basics", title="SELECT basics"),
        RoadmapNode(id="window_functions", title="Window Functions"),
    ]
    edges = [RoadmapEdge(source="select_basics", target="window_functions")]

    roadmap = _service(engine).build_roadmap("goal_1", nodes, edges)

    assert roadmap.version == 1
    assert roadmap.status == RoadmapStatus.ACTIVE
    concepts = SqlConceptRepository(engine)
    assert {c.id for c in concepts.list_by_goal("goal_1")} == {"select_basics", "window_functions"}
    relations = SqlConceptRelationRepository(engine)
    assert [r.source_id for r in relations.list_prerequisites_of("window_functions")] == [
        "select_basics"
    ]


def test_build_roadmap_raises_when_goal_not_found_without_writing_anything(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    with pytest.raises(GoalNotFoundError):
        _service(engine).build_roadmap("missing_goal", [RoadmapNode(id="x", title="X")], [])

    assert SqlConceptRepository(engine).get("x") is None


def test_build_roadmap_rejects_duplicate_node_ids(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    nodes = [RoadmapNode(id="a", title="A"), RoadmapNode(id="a", title="A again")]

    with pytest.raises(RoadmapValidationError, match="duplicate"):
        _service(engine).build_roadmap("goal_1", nodes, [])


def test_build_roadmap_rejects_self_relation(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    nodes = [RoadmapNode(id="a", title="A")]
    edges = [RoadmapEdge(source="a", target="a")]

    with pytest.raises(RoadmapValidationError, match="self-relation"):
        _service(engine).build_roadmap("goal_1", nodes, edges)


def test_build_roadmap_rejects_dangling_edge_ids(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    nodes = [RoadmapNode(id="a", title="A")]
    edges = [RoadmapEdge(source="a", target="unknown_node")]

    with pytest.raises(RoadmapValidationError, match="unknown node id"):
        _service(engine).build_roadmap("goal_1", nodes, edges)


def test_build_roadmap_rejects_cycles(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    nodes = [
        RoadmapNode(id="a", title="A"),
        RoadmapNode(id="b", title="B"),
        RoadmapNode(id="c", title="C"),
    ]
    edges = [
        RoadmapEdge(source="a", target="b"),
        RoadmapEdge(source="b", target="c"),
        RoadmapEdge(source="c", target="a"),
    ]

    with pytest.raises(RoadmapValidationError, match="cycle"):
        _service(engine).build_roadmap("goal_1", nodes, edges)


def test_build_roadmap_never_overwrites_evidence_derived_fields_on_existing_concept(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    concepts = SqlConceptRepository(engine)
    concepts.add(
        Concept(
            id="window_functions",
            title="Old title",
            domain="sql",
            status=ConceptStatus.USABLE,
            mastery=3.2,
            confidence=70,
            importance=2,
            retention=55,
            created_at=NOW,
            updated_at=NOW,
        )
    )

    _service(engine).build_roadmap(
        "goal_1", [RoadmapNode(id="window_functions", title="Window Functions", importance=5)], []
    )

    updated = concepts.get("window_functions")
    assert updated is not None
    assert updated.title == "Window Functions"
    assert updated.importance == 5
    assert updated.mastery == 3.2
    assert updated.status == ConceptStatus.USABLE
    assert updated.confidence == 70
    assert updated.retention == 55


def test_node_domain_falls_back_to_goal_domain(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine, domain="sql")

    _service(engine).build_roadmap("goal_1", [RoadmapNode(id="a", title="A")], [])

    concept = SqlConceptRepository(engine).get("a")
    assert concept is not None
    assert concept.domain == "sql"


def test_node_without_domain_and_goal_without_domain_raises(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine, domain=None)

    with pytest.raises(RoadmapValidationError, match="domain"):
        _service(engine).build_roadmap("goal_1", [RoadmapNode(id="a", title="A")], [])


def test_rebuilding_roadmap_supersedes_the_previous_version(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    service = _service(engine)
    first = service.build_roadmap("goal_1", [RoadmapNode(id="a", title="A")], [])

    second = service.build_roadmap("goal_1", [RoadmapNode(id="a", title="A")], [])

    assert second.version == 2
    assert second.status == RoadmapStatus.ACTIVE
    roadmaps = SqlRoadmapRepository(engine)
    assert roadmaps.get_active_for_goal("goal_1") == second
    assert first.id != second.id


def test_rebuilding_the_same_roadmap_is_idempotent_for_edges(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    nodes = [RoadmapNode(id="a", title="A"), RoadmapNode(id="b", title="B")]
    edges = [RoadmapEdge(source="a", target="b")]
    service = _service(engine)
    service.build_roadmap("goal_1", nodes, edges)

    service.build_roadmap("goal_1", nodes, edges)  # must not raise a duplicate-key error

    relations = SqlConceptRelationRepository(engine)
    assert len(relations.list_prerequisites_of("b")) == 1


def test_edge_relation_type_is_preserved(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    nodes = [RoadmapNode(id="a", title="A"), RoadmapNode(id="b", title="B")]
    edges = [RoadmapEdge(source="a", target="b", relation=ConceptRelationType.RELATED_TO)]

    _service(engine).build_roadmap("goal_1", nodes, edges)

    relations = SqlConceptRelationRepository(engine)
    found = relations.list_relations_from("a")
    assert [(r.target_id, r.relation) for r in found] == [("b", ConceptRelationType.RELATED_TO)]


def test_get_roadmap_returns_the_active_graph(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    nodes = [RoadmapNode(id="a", title="A"), RoadmapNode(id="b", title="B")]
    edges = [RoadmapEdge(source="a", target="b")]
    service = _service(engine)
    built = service.build_roadmap("goal_1", nodes, edges)

    graph = service.get_roadmap("goal_1")

    assert graph.roadmap == built
    assert {c.id for c in graph.nodes} == {"a", "b"}
    assert [(e.source_id, e.target_id) for e in graph.edges] == [("a", "b")]


def test_get_roadmap_raises_when_goal_missing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    with pytest.raises(GoalNotFoundError):
        _service(engine).get_roadmap("missing")


def test_get_roadmap_raises_when_no_roadmap_generated_yet(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)

    with pytest.raises(RoadmapNotFoundError):
        _service(engine).get_roadmap("goal_1")


def test_get_roadmap_reflects_the_latest_version_after_recalculation(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    service = _service(engine)
    service.build_roadmap("goal_1", [RoadmapNode(id="a", title="A")], [])
    second = service.build_roadmap(
        "goal_1", [RoadmapNode(id="a", title="A"), RoadmapNode(id="b", title="B")], []
    )

    graph = service.get_roadmap("goal_1")

    assert graph.roadmap == second
    assert graph.roadmap.version == 2
