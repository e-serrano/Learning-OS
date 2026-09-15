from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import ConceptRelationType, ConceptStatus
from app.domain.value_objects import ConfidencePercent, FiveLevelScale, Mastery, RetentionPercent


class Concept(BaseModel):
    id: str
    title: str
    domain: str
    status: ConceptStatus
    mastery: Mastery
    confidence: ConfidencePercent
    importance: FiveLevelScale
    retention: RetentionPercent
    last_practiced: datetime | None = None
    next_review: datetime | None = None
    obsidian_path: str | None = None
    created_at: datetime
    updated_at: datetime


class ConceptRelation(BaseModel):
    """An edge between two concepts -- see docs/DATABASE_SCHEMA.md concept_relations."""

    source_id: str
    target_id: str
    relation: ConceptRelationType
    weight: float | None = None
