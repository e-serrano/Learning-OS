from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Evaluation(BaseModel):
    """AI evaluations are evidence, not absolute truth -- see docs/DOMAIN_MODEL.md #9.

    Treated as immutable like other evidentiary records (docs/AGENTS.md #23).
    """

    model_config = ConfigDict(frozen=True)

    id: str
    attempt_id: str
    correctness: float
    reasoning: float
    completeness: float
    independence: float
    transfer: float
    misconceptions: list[str] = Field(default_factory=list)
    feedback: str
    recommended_action: str
    provider: str
    model: str
    prompt_version: str
    created_at: datetime
