"""Roadmap service -- validates a proposed roadmap graph (dangling IDs,
self-relations, cycles) and persists it as Concepts, ConceptRelations,
and a versioned Roadmap marker (docs/TASKS.md T068).

Input is the planner's `roadmap_nodes`/`roadmap_edges` (T067,
docs/AI_CONTRACTS.md #4) -- untyped dicts in the AI contract because
AI_CONTRACTS.md never pins their shape beyond an empty example. This
service defines and enforces that shape via `RoadmapNode`/`RoadmapEdge`.

The graph itself is not duplicated into the `roadmaps` table --
"nodes reference concepts and skills, edges contain a relationship
type" (docs/DOMAIN_MODEL.md #16) already means the graph lives in
`goal_concepts` (membership) and `concept_relations` (edges); a Roadmap
row is only the versioned active/superseded marker.

"AI proposes. The Learning Engine decides." -- this is the decision
point: a malformed or cyclic graph is rejected before a single row is
written.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.entities import Concept, ConceptRelation, Roadmap
from app.domain.enums import ConceptRelationType, ConceptStatus, RoadmapStatus
from app.domain.ports import (
    ClockPort,
    ConceptRelationRepository,
    ConceptRepository,
    GoalRepository,
    IdGeneratorPort,
    RoadmapRepository,
)
from app.services.context_builder import GoalNotFoundError


class RoadmapValidationError(Exception):
    pass


class RoadmapNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class RoadmapNode:
    id: str
    title: str
    importance: int = 3
    domain: str | None = None


@dataclass(frozen=True)
class RoadmapEdge:
    source: str
    target: str
    relation: ConceptRelationType = ConceptRelationType.PREREQUISITE_OF


@dataclass(frozen=True)
class RoadmapGraph:
    roadmap: Roadmap
    nodes: list[Concept]
    edges: list[ConceptRelation]


def _validate(nodes: list[RoadmapNode], edges: list[RoadmapEdge]) -> None:
    node_ids = [n.id for n in nodes]
    if len(set(node_ids)) != len(node_ids):
        raise RoadmapValidationError("duplicate node ids in roadmap")

    node_id_set = set(node_ids)
    graph: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    for edge in edges:
        if edge.source == edge.target:
            raise RoadmapValidationError(f"self-relation on node {edge.source!r}")
        if edge.source not in node_id_set:
            raise RoadmapValidationError(f"edge references unknown node id {edge.source!r}")
        if edge.target not in node_id_set:
            raise RoadmapValidationError(f"edge references unknown node id {edge.target!r}")
        graph[edge.source].add(edge.target)

    _assert_acyclic(graph)


def _assert_acyclic(graph: dict[str, set[str]]) -> None:
    unvisited, in_progress, done = 0, 1, 2
    state = dict.fromkeys(graph, unvisited)

    def visit(node: str) -> None:
        state[node] = in_progress
        for neighbor in graph[node]:
            if state[neighbor] == in_progress:
                raise RoadmapValidationError(f"cycle detected: {node!r} -> {neighbor!r}")
            if state[neighbor] == unvisited:
                visit(neighbor)
        state[node] = done

    for node in graph:
        if state[node] == unvisited:
            visit(node)


class RoadmapService:
    def __init__(
        self,
        goals: GoalRepository,
        concepts: ConceptRepository,
        concept_relations: ConceptRelationRepository,
        roadmaps: RoadmapRepository,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._goals = goals
        self._concepts = concepts
        self._concept_relations = concept_relations
        self._roadmaps = roadmaps
        self._clock = clock
        self._ids = ids

    def build_roadmap(
        self, goal_id: str, nodes: list[RoadmapNode], edges: list[RoadmapEdge]
    ) -> Roadmap:
        goal = self._goals.get(goal_id)
        if goal is None:
            raise GoalNotFoundError(goal_id)

        _validate(nodes, edges)

        now = self._clock.now()
        for node in nodes:
            self._upsert_concept(node, goal_domain=goal.domain, now=now)
            self._concepts.link_to_goal(goal_id, node.id, importance=node.importance)
        for edge in edges:
            self._add_edge_if_new(edge)

        previous = self._roadmaps.get_active_for_goal(goal_id)
        if previous is not None:
            self._roadmaps.update(previous.model_copy(update={"status": RoadmapStatus.SUPERSEDED}))

        roadmap = Roadmap(
            id=self._ids.new_id("roadmap"),
            goal_id=goal_id,
            version=(previous.version + 1) if previous is not None else 1,
            status=RoadmapStatus.ACTIVE,
        )
        self._roadmaps.add(roadmap)
        return roadmap

    def get_roadmap(self, goal_id: str) -> RoadmapGraph:
        """Read side of T068 (docs/TASKS.md T101, docs/API_SPEC.md #4:
        `GET /goals/{id}/roadmap`). The graph isn't stored on the
        `Roadmap` row itself (see module docstring) -- it's reassembled
        from every concept linked to the goal plus each one's outgoing
        relations."""
        if self._goals.get(goal_id) is None:
            raise GoalNotFoundError(goal_id)

        roadmap = self._roadmaps.get_active_for_goal(goal_id)
        if roadmap is None:
            raise RoadmapNotFoundError(goal_id)

        nodes = self._concepts.list_by_goal(goal_id)
        edges: list[ConceptRelation] = []
        for node in nodes:
            edges.extend(self._concept_relations.list_relations_from(node.id))

        return RoadmapGraph(roadmap=roadmap, nodes=nodes, edges=edges)

    def _upsert_concept(self, node: RoadmapNode, goal_domain: str | None, now: datetime) -> None:
        domain = node.domain or goal_domain
        if domain is None:
            raise RoadmapValidationError(
                f"node {node.id!r} has no domain and the goal has none to fall back to"
            )

        existing = self._concepts.get(node.id)
        if existing is None:
            self._concepts.add(
                Concept(
                    id=node.id,
                    title=node.title,
                    domain=domain,
                    status=ConceptStatus.UNKNOWN,
                    mastery=0,
                    confidence=0,
                    importance=node.importance,
                    retention=0,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            # mastery/confidence/retention/status are evidence-derived
            # (docs/DOMAIN_MODEL.md #4) -- the roadmap never touches them.
            self._concepts.update(
                existing.model_copy(
                    update={
                        "title": node.title,
                        "domain": domain,
                        "importance": node.importance,
                        "updated_at": now,
                    }
                )
            )

    def _add_edge_if_new(self, edge: RoadmapEdge) -> None:
        already_exists = any(
            relation.target_id == edge.target and relation.relation == edge.relation
            for relation in self._concept_relations.list_relations_from(edge.source)
        )
        if already_exists:
            return
        self._concept_relations.add(
            ConceptRelation(source_id=edge.source, target_id=edge.target, relation=edge.relation)
        )
