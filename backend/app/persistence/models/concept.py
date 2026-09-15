from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class ConceptModel(Base):
    __tablename__ = "concepts"
    __table_args__ = (Index("idx_concepts_next_review", "next_review"),)

    id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    domain: Mapped[str]
    status: Mapped[str]
    mastery: Mapped[float] = mapped_column(default=0)
    confidence: Mapped[float] = mapped_column(default=0)
    importance: Mapped[int] = mapped_column(default=3)
    retention: Mapped[float] = mapped_column(default=0)
    last_practiced: Mapped[str | None]
    next_review: Mapped[str | None]
    obsidian_path: Mapped[str | None]
    created_at: Mapped[str]
    updated_at: Mapped[str]


class ConceptRelationModel(Base):
    __tablename__ = "concept_relations"

    source_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), primary_key=True)
    target_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), primary_key=True)
    relation: Mapped[str] = mapped_column(primary_key=True)
    weight: Mapped[float | None]
