from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ExerciseType
from app.domain.value_objects import ConfidencePercent, FiveLevelScale


class Exercise(BaseModel):
    id: str
    type: ExerciseType
    difficulty: FiveLevelScale
    goal_id: str
    concept_ids: list[str] = Field(default_factory=list)
    skill_ids: list[str] = Field(default_factory=list)
    prerequisite_ids: list[str] = Field(default_factory=list)
    prompt: str
    success_criteria: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    solution: str
    common_mistakes: list[str] = Field(default_factory=list)
    transfer_variant: str | None = None
    created_at: datetime


class ExerciseAttempt(BaseModel):
    """Immutable -- see docs/DOMAIN_MODEL.md #8."""

    model_config = ConfigDict(frozen=True)

    id: str
    exercise_id: str
    session_id: str
    answer: str
    confidence: ConfidencePercent
    submitted_at: datetime
    evaluation_id: str | None = None
