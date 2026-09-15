from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class MistakeModel(Base):
    __tablename__ = "mistakes"
    __table_args__ = (Index("idx_mistakes_concept", "concept_id", "resolved_at"),)

    id: Mapped[str] = mapped_column(primary_key=True)
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id"))
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"))
    type: Mapped[str]
    description: Mapped[str]
    severity: Mapped[str]
    occurrences: Mapped[int] = mapped_column(default=1)
    first_seen: Mapped[str]
    last_seen: Mapped[str]
    resolved_at: Mapped[str | None]
