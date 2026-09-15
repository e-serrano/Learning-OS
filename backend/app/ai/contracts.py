"""Structured AI response contracts -- see docs/AI_CONTRACTS.md #4-10.

Every field the model must supply is typed and validated; the model never
has free rein over anything downstream mutates state with. Application
code owns turning these into evidence, mastery updates, or vault writes
(docs/AGENTS.md #5, #9).
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.enums import ExerciseType, ProposalOperation
from app.domain.value_objects import FiveLevelScale, NormalizedScore


class HighLeverageConcept(BaseModel):
    concept_id: str
    title: str
    importance: FiveLevelScale
    reason: str


class PlannerResponse(BaseModel):
    """docs/AI_CONTRACTS.md #4."""

    high_leverage_concepts: list[HighLeverageConcept] = Field(default_factory=list)
    deferred_topics: list[str] = Field(default_factory=list)
    roadmap_nodes: list[dict[str, object]] = Field(default_factory=list)
    roadmap_edges: list[dict[str, object]] = Field(default_factory=list)
    diagnostic_focus: list[str] = Field(default_factory=list)


class DiagnosticItem(BaseModel):
    concept_id: str
    evidence_type: Literal["recall", "application", "transfer"]
    question: str
    difficulty: FiveLevelScale


class DiagnosticianResponse(BaseModel):
    """docs/AI_CONTRACTS.md #5."""

    items: list[DiagnosticItem] = Field(default_factory=list)


class TutorResponse(BaseModel):
    """docs/AI_CONTRACTS.md #6. Must not reveal exercise solutions unless
    the caller's policy explicitly allows it -- enforced by the caller,
    not this schema."""

    mode: Literal["explain", "question", "hint", "feedback", "reflection"]
    content: str
    check_for_understanding: str | None = None
    next_activity: str | None = None


class ExerciseGeneratorResponse(BaseModel):
    """docs/AI_CONTRACTS.md #7."""

    type: ExerciseType
    difficulty: FiveLevelScale
    prompt: str
    success_criteria: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    solution: str
    common_mistakes: list[str] = Field(default_factory=list)
    transfer_variant: str | None = None


class EvaluatorResponse(BaseModel):
    """docs/AI_CONTRACTS.md #8. AI evaluations are evidence, not absolute
    truth (docs/DOMAIN_MODEL.md #9) -- the caller converts this into an
    Evaluation/Evidence record, never assigns mastery directly."""

    correctness: NormalizedScore
    reasoning: NormalizedScore
    completeness: NormalizedScore
    independence: NormalizedScore
    transfer: NormalizedScore
    misconceptions: list[str] = Field(default_factory=list)
    feedback: str
    recommended_action: str


class CuratorOperation(BaseModel):
    path: str
    operation: ProposalOperation
    section: str | None = None
    content: str


class CuratorResponse(BaseModel):
    """docs/AI_CONTRACTS.md #9. The application validates every operation
    (T081) before it ever becomes a ChangeProposal -- this schema only
    constrains the shape, not path safety or vault semantics."""

    operations: list[CuratorOperation] = Field(default_factory=list)


class CalibrationBreakdown(BaseModel):
    overconfidence: NormalizedScore
    underconfidence: NormalizedScore


class ProgressResponse(BaseModel):
    """docs/AI_CONTRACTS.md #10."""

    progress_summary: str
    mastered: list[str] = Field(default_factory=list)
    weak: list[str] = Field(default_factory=list)
    recurring_mistakes: list[str] = Field(default_factory=list)
    calibration: CalibrationBreakdown
    recommendations: list[str] = Field(default_factory=list)
