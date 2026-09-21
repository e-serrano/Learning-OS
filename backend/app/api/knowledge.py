"""Knowledge routes (docs/TASKS.md T100, docs/API_SPEC.md #3).

Spans two path prefixes (`/goals/{goal_id}/knowledge` and
`/concepts/...`), so unlike goals.py/vault.py/providers.py this router
has no single fixed prefix -- only the shared `/api/v1` base.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_knowledge_explorer_service
from app.api.errors import api_error
from app.domain.entities import Concept, ConceptRelation
from app.domain.enums import ConceptRelationType, ConceptStatus
from app.domain.value_objects import ConfidencePercent, FiveLevelScale, Mastery, RetentionPercent
from app.services.knowledge_explorer_service import (
    ConceptNotFoundError,
    GoalNotFoundError,
    KnowledgeExplorerService,
)

router = APIRouter(prefix="/api/v1", tags=["knowledge"])

KnowledgeExplorerServiceDep = Annotated[
    KnowledgeExplorerService, Depends(get_knowledge_explorer_service)
]


class ConceptResponse(BaseModel):
    id: str
    title: str
    domain: str
    status: ConceptStatus
    mastery: Mastery
    confidence: ConfidencePercent
    importance: FiveLevelScale
    retention: RetentionPercent
    last_practiced: datetime | None
    next_review: datetime | None
    obsidian_path: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, concept: Concept) -> "ConceptResponse":
        return cls(**concept.model_dump())


class ConceptListResponse(BaseModel):
    concepts: list[ConceptResponse]


class ConceptRelationResponse(BaseModel):
    source_id: str
    target_id: str
    relation: ConceptRelationType
    weight: float | None

    @classmethod
    def from_entity(cls, relation: ConceptRelation) -> "ConceptRelationResponse":
        return cls(**relation.model_dump())


class ConceptRelationListResponse(BaseModel):
    relations: list[ConceptRelationResponse]


@router.get("/goals/{goal_id}/knowledge", response_model=ConceptListResponse)
def list_knowledge(
    goal_id: str,
    service: KnowledgeExplorerServiceDep,
    status: ConceptStatus | None = None,
    mastery_lt: float | None = None,
    next_review_before: datetime | None = None,
) -> ConceptListResponse:
    try:
        concepts = service.list_concepts(
            goal_id,
            status=status,
            mastery_lt=mastery_lt,
            next_review_before=next_review_before,
        )
    except GoalNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Goal '{goal_id}' not found", 404) from exc
    return ConceptListResponse(concepts=[ConceptResponse.from_entity(c) for c in concepts])


@router.get("/concepts/{concept_id}", response_model=ConceptResponse)
def get_concept(concept_id: str, service: KnowledgeExplorerServiceDep) -> ConceptResponse:
    try:
        concept = service.get_concept(concept_id)
    except ConceptNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Concept '{concept_id}' not found", 404) from exc
    return ConceptResponse.from_entity(concept)


@router.get("/concepts/{concept_id}/relations", response_model=ConceptRelationListResponse)
def list_concept_relations(
    concept_id: str, service: KnowledgeExplorerServiceDep
) -> ConceptRelationListResponse:
    try:
        relations = service.list_relations(concept_id)
    except ConceptNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Concept '{concept_id}' not found", 404) from exc
    return ConceptRelationListResponse(
        relations=[ConceptRelationResponse.from_entity(r) for r in relations]
    )
