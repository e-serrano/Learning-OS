from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class GoalModel(Base):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    description: Mapped[str | None]
    domain: Mapped[str | None]
    target_level: Mapped[str]
    status: Mapped[str]
    priority: Mapped[int] = mapped_column(default=3)
    deadline: Mapped[str | None]
    available_minutes_per_week: Mapped[int | None]
    created_at: Mapped[str]
    updated_at: Mapped[str]


class GoalConceptModel(Base):
    """Importance/state can eventually become goal-specific (docs/DATABASE_SCHEMA.md)."""

    __tablename__ = "goal_concepts"

    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id"), primary_key=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), primary_key=True)
    importance: Mapped[int] = mapped_column(default=3)
