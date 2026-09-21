"""Roadmap routes (docs/TASKS.md T101, docs/API_SPEC.md #4).

`generate` and `recalculate` are the same operation
(`RoadmapGenerationService.generate_roadmap`, see its own docstring):
`RoadmapService.build_roadmap` already supersedes any existing active
roadmap and bumps the version, so there is nothing recalculate needs to
do differently.

First route in the codebase that actually calls the AI orchestrator
over HTTP, so it is also the first to translate `AIProviderUnavailableError`/
`AIInvalidOutputError` (docs/AI_CONTRACTS.md #13) into the matching
`AI_UNAVAILABLE`/`AI_INVALID_OUTPUT` error codes (docs/API_SPEC.md #11).
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.api.dependencies import get_roadmap_generation_service, get_roadmap_service
from app.api.errors import api_error
from app.domain.entities import Concept, ConceptRelation, Roadmap
from app.domain.enums import ConceptRelationType, ConceptStatus, RoadmapStatus
from app.domain.value_objects import ConfidencePercent, FiveLevelScale, Mastery
from app.services.context_builder import GoalNotFoundError
from app.services.roadmap_generation_service import RoadmapGenerationService
from app.services.roadmap_service import (
    RoadmapGraph,
    RoadmapNotFoundError,
    RoadmapService,
    RoadmapValidationError,
)

router = APIRouter(prefix="/api/v1/goals/{goal_id}/roadmap", tags=["roadmap"])

RoadmapServiceDep = Annotated[RoadmapService, Depends(get_roadmap_service)]
RoadmapGenerationServiceDep = Annotated[
    RoadmapGenerationService, Depends(get_roadmap_generation_service)
]


class RoadmapNodeResponse(BaseModel):
    id: str
    title: str
    domain: str
    status: ConceptStatus
    mastery: Mastery
    confidence: ConfidencePercent
    importance: FiveLevelScale

    @classmethod
    def from_entity(cls, concept: Concept) -> "RoadmapNodeResponse":
        return cls(
            id=concept.id,
            title=concept.title,
            domain=concept.domain,
            status=concept.status,
            mastery=concept.mastery,
            confidence=concept.confidence,
            importance=concept.importance,
        )


class RoadmapEdgeResponse(BaseModel):
    source_id: str
    target_id: str
    relation: ConceptRelationType

    @classmethod
    def from_entity(cls, relation: ConceptRelation) -> "RoadmapEdgeResponse":
        return cls(**relation.model_dump())


class RoadmapResponse(BaseModel):
    id: str
    goal_id: str
    version: int
    status: RoadmapStatus
    nodes: list[RoadmapNodeResponse]
    edges: list[RoadmapEdgeResponse]

    @classmethod
    def from_graph(cls, graph: RoadmapGraph) -> "RoadmapResponse":
        return cls(
            id=graph.roadmap.id,
            goal_id=graph.roadmap.goal_id,
            version=graph.roadmap.version,
            status=graph.roadmap.status,
            nodes=[RoadmapNodeResponse.from_entity(c) for c in graph.nodes],
            edges=[RoadmapEdgeResponse.from_entity(r) for r in graph.edges],
        )


async def _generate(goal_id: str, service: RoadmapGenerationServiceDep) -> Roadmap:
    try:
        return await service.generate_roadmap(goal_id)
    except GoalNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Goal '{goal_id}' not found", 404) from exc
    except RoadmapValidationError as exc:
        raise api_error("AI_INVALID_OUTPUT", str(exc), 422) from exc
    except AIInvalidOutputError as exc:
        raise api_error("AI_INVALID_OUTPUT", str(exc), 422) from exc
    except AIProviderUnavailableError as exc:
        raise api_error("AI_UNAVAILABLE", str(exc), 503) from exc


async def _generate_and_respond(
    goal_id: str,
    generation_service: RoadmapGenerationServiceDep,
    roadmap_service: RoadmapServiceDep,
) -> RoadmapResponse:
    await _generate(goal_id, generation_service)
    return RoadmapResponse.from_graph(roadmap_service.get_roadmap(goal_id))


@router.post("/generate", response_model=RoadmapResponse)
async def generate_roadmap(
    goal_id: str,
    generation_service: RoadmapGenerationServiceDep,
    roadmap_service: RoadmapServiceDep,
) -> RoadmapResponse:
    return await _generate_and_respond(goal_id, generation_service, roadmap_service)


@router.get("", response_model=RoadmapResponse)
def get_roadmap(goal_id: str, service: RoadmapServiceDep) -> RoadmapResponse:
    try:
        graph = service.get_roadmap(goal_id)
    except GoalNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Goal '{goal_id}' not found", 404) from exc
    except RoadmapNotFoundError as exc:
        raise api_error("NOT_FOUND", f"No roadmap generated yet for goal '{goal_id}'", 404) from exc
    return RoadmapResponse.from_graph(graph)


@router.post("/recalculate", response_model=RoadmapResponse)
async def recalculate_roadmap(
    goal_id: str,
    generation_service: RoadmapGenerationServiceDep,
    roadmap_service: RoadmapServiceDep,
) -> RoadmapResponse:
    return await _generate_and_respond(goal_id, generation_service, roadmap_service)
