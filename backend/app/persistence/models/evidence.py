from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class EvidenceModel(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        Index("idx_evidence_concept_time", "concept_id", "timestamp"),
        Index("idx_evidence_goal_time", "goal_id", "timestamp"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id"))
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"))
    activity_id: Mapped[str] = mapped_column(ForeignKey("activities.id"))
    source_type: Mapped[str]
    difficulty: Mapped[int]
    correctness: Mapped[float | None]
    reasoning: Mapped[float | None]
    independence: Mapped[float | None]
    transfer: Mapped[float | None]
    confidence: Mapped[float | None]
    timestamp: Mapped[str]
    metadata_json: Mapped[str]
