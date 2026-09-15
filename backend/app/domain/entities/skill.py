from pydantic import BaseModel, Field

from app.domain.value_objects import Mastery


class Skill(BaseModel):
    id: str
    title: str
    description: str
    mastery: Mastery
    concept_ids: list[str] = Field(default_factory=list)
