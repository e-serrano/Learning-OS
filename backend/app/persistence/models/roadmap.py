from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class RoadmapModel(Base):
    __tablename__ = "roadmaps"
    __table_args__ = (Index("idx_roadmaps_goal_version", "goal_id", "version", unique=True),)

    id: Mapped[str] = mapped_column(primary_key=True)
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id"))
    version: Mapped[int]
    status: Mapped[str]
