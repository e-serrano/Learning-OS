from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(primary_key=True)
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id"))
    title: Mapped[str]
    objective: Mapped[str]
    difficulty: Mapped[int]
    status: Mapped[str]
    success_criteria_json: Mapped[str]
    artifact_path: Mapped[str | None]
    created_at: Mapped[str]


class ProjectConceptModel(Base):
    __tablename__ = "project_concepts"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), primary_key=True)
