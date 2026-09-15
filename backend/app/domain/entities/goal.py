from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import GoalStatus, TargetLevel


class LearningGoal(BaseModel):
    id: str
    title: str
    description: str | None = None
    domain: str | None = None
    target_level: TargetLevel
    status: GoalStatus
    priority: int
    deadline: datetime | None = None
    available_minutes_per_week: int | None = None
    created_at: datetime
    updated_at: datetime
