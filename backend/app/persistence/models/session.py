from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(primary_key=True)
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id"))
    mode: Mapped[str]
    objective: Mapped[str]
    status: Mapped[str]
    started_at: Mapped[str | None]
    ended_at: Mapped[str | None]
    created_at: Mapped[str]


class ActivityModel(Base):
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    type: Mapped[str]
    sequence: Mapped[int]
    status: Mapped[str]
    payload_json: Mapped[str]
    created_at: Mapped[str]
