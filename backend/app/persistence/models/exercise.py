from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class ExerciseModel(Base):
    __tablename__ = "exercises"

    id: Mapped[str] = mapped_column(primary_key=True)
    type: Mapped[str]
    difficulty: Mapped[int]
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id"))
    prompt: Mapped[str]
    solution: Mapped[str]
    metadata_json: Mapped[str]
    created_at: Mapped[str]


class ExerciseConceptModel(Base):
    __tablename__ = "exercise_concepts"

    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), primary_key=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), primary_key=True)


class ExerciseAttemptModel(Base):
    __tablename__ = "exercise_attempts"

    id: Mapped[str] = mapped_column(primary_key=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    answer: Mapped[str]
    confidence: Mapped[float | None]
    submitted_at: Mapped[str]
