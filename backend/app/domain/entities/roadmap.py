from pydantic import BaseModel

from app.domain.enums import RoadmapStatus


class Roadmap(BaseModel):
    id: str
    goal_id: str
    version: int
    status: RoadmapStatus
