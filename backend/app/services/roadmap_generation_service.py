"""Roadmap generation -- chains `PlannerService` (T067) and
`RoadmapService` (T068) into the actual `POST /goals/{id}/roadmap/generate`
and `POST /goals/{id}/roadmap/recalculate` actions (docs/TASKS.md T101,
docs/API_SPEC.md #4).

Both API routes call this same method: `RoadmapService.build_roadmap()`
already supersedes any existing active roadmap and bumps the version, so
"generate" (first time) and "recalculate" (after more evidence) are the
same operation underneath -- there is no separate code path to write.

`PlannerResponse.roadmap_nodes`/`roadmap_edges` are raw
`list[dict[str, object]]` -- AI_CONTRACTS.md #4 never pins their shape
beyond an empty `[]` example (roadmap_service.py's own docstring already
flags this), so converting them into typed `RoadmapNode`/`RoadmapEdge`
is real, new validation surface: a malformed dict (missing `id`/`title`
for a node, missing `source`/`target` for an edge) raises the same
`RoadmapValidationError` `build_roadmap` already raises for a
structurally bad graph -- one single error surface for "the AI proposed
something unusable". Fields with a sensible default on `RoadmapNode`/
`RoadmapEdge` (`importance`, `domain`, `relation`) fall back to that
default instead of failing outright when missing or malformed.
"""

from app.domain.entities import Roadmap
from app.domain.enums import ConceptRelationType
from app.services.planner_service import PlannerService
from app.services.roadmap_service import (
    RoadmapEdge,
    RoadmapNode,
    RoadmapService,
    RoadmapValidationError,
)


def _node_from_dict(raw: dict[str, object]) -> RoadmapNode:
    node_id = raw.get("id")
    title = raw.get("title")
    if not isinstance(node_id, str) or not node_id:
        raise RoadmapValidationError(f"roadmap node missing a valid 'id': {raw!r}")
    if not isinstance(title, str) or not title:
        raise RoadmapValidationError(f"roadmap node {node_id!r} missing a valid 'title'")

    importance = raw.get("importance", 3)
    if not isinstance(importance, int) or not (1 <= importance <= 5):
        importance = 3

    domain = raw.get("domain")
    if not isinstance(domain, str):
        domain = None

    return RoadmapNode(id=node_id, title=title, importance=importance, domain=domain)


def _edge_from_dict(raw: dict[str, object]) -> RoadmapEdge:
    source = raw.get("source")
    target = raw.get("target")
    if not isinstance(source, str) or not source:
        raise RoadmapValidationError(f"roadmap edge missing a valid 'source': {raw!r}")
    if not isinstance(target, str) or not target:
        raise RoadmapValidationError(f"roadmap edge missing a valid 'target': {raw!r}")

    relation_raw = raw.get("relation")
    try:
        relation = ConceptRelationType(relation_raw) if isinstance(relation_raw, str) else None
    except ValueError:
        relation = None
    if relation is None:
        relation = ConceptRelationType.PREREQUISITE_OF

    return RoadmapEdge(source=source, target=target, relation=relation)


class RoadmapGenerationService:
    def __init__(self, planner: PlannerService, roadmaps: RoadmapService) -> None:
        self._planner = planner
        self._roadmaps = roadmaps

    async def generate_roadmap(self, goal_id: str) -> Roadmap:
        plan = await self._planner.plan(goal_id)
        nodes = [_node_from_dict(n) for n in plan.roadmap_nodes]
        edges = [_edge_from_dict(e) for e in plan.roadmap_edges]
        return self._roadmaps.build_roadmap(goal_id, nodes, edges)
