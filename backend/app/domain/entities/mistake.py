from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import MistakeSeverity, MistakeType


class Mistake(BaseModel):
    id: str
    concept_id: str
    goal_id: str
    type: MistakeType
    description: str
    severity: MistakeSeverity
    occurrences: int
    first_seen: datetime
    last_seen: datetime
    resolved_at: datetime | None = None
