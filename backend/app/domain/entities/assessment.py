from pydantic import BaseModel, Field

from app.domain.enums import AssessmentType


class Assessment(BaseModel):
    id: str
    goal_id: str
    type: AssessmentType
    target_concept_ids: list[str] = Field(default_factory=list)
    difficulty: int
