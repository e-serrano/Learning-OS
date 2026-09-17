from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import ActivityStatus, ActivityType, SessionMode, SessionStatus


class Session(BaseModel):
    id: str
    goal_id: str
    mode: SessionMode
    objective: str
    status: SessionStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None


class Activity(BaseModel):
    id: str
    session_id: str
    type: ActivityType
    sequence: int
    concept_ids: list[str] = Field(default_factory=list)
    status: ActivityStatus
    exercise_id: str | None = None
