from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import ReviewStatus


class Review(BaseModel):
    id: str
    concept_id: str
    goal_id: str
    scheduled_at: datetime
    completed_at: datetime | None = None
    interval_days: float
    stability: float | None = None
    difficulty: float | None = None
    status: ReviewStatus
