from pydantic import BaseModel, Field

from app.domain.enums import ProjectStatus


class Project(BaseModel):
    id: str
    goal_id: str
    title: str
    objective: str
    difficulty: int
    status: ProjectStatus
    success_criteria: list[str] = Field(default_factory=list)
    artifact_path: str | None = None
