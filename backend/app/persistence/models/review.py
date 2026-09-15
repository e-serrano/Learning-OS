from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class ReviewModel(Base):
    __tablename__ = "reviews"
    __table_args__ = (Index("idx_reviews_schedule", "scheduled_at", "status"),)

    id: Mapped[str] = mapped_column(primary_key=True)
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id"))
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"))
    scheduled_at: Mapped[str]
    completed_at: Mapped[str | None]
    interval_days: Mapped[float]
    stability: Mapped[float | None]
    difficulty: Mapped[float | None]
    status: Mapped[str]
