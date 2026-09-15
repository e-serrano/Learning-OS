from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class EvaluationModel(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("exercise_attempts.id"))
    correctness: Mapped[float]
    reasoning: Mapped[float]
    completeness: Mapped[float]
    independence: Mapped[float]
    transfer: Mapped[float]
    feedback: Mapped[str]
    misconceptions_json: Mapped[str]
    recommended_action: Mapped[str]
    provider: Mapped[str | None]
    model: Mapped[str | None]
    prompt_version: Mapped[str | None]
    created_at: Mapped[str]
