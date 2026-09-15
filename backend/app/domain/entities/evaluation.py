from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.value_objects import NormalizedScore


class Evaluation(BaseModel):
    """AI evaluations are evidence, not absolute truth -- see docs/DOMAIN_MODEL.md #9.

    Treated as immutable like other evidentiary records (docs/AGENTS.md #23).
    """

    model_config = ConfigDict(frozen=True)

    id: str
    attempt_id: str
    correctness: NormalizedScore
    reasoning: NormalizedScore
    completeness: NormalizedScore
    independence: NormalizedScore
    transfer: NormalizedScore
    misconceptions: list[str] = Field(default_factory=list)
    feedback: str
    recommended_action: str
    provider: str
    model: str
    prompt_version: str
    created_at: datetime
