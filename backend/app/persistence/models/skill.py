from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class SkillModel(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    description: Mapped[str | None]
    mastery: Mapped[float] = mapped_column(default=0)
    created_at: Mapped[str]
    updated_at: Mapped[str]


class SkillConceptModel(Base):
    __tablename__ = "skill_concepts"

    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), primary_key=True)
