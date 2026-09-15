from pydantic import BaseModel, Field


class Skill(BaseModel):
    id: str
    title: str
    description: str
    mastery: float
    concept_ids: list[str] = Field(default_factory=list)
