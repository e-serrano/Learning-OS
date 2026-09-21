from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.domain.entities import Concept, LearningGoal, Review, Session
from app.domain.enums import (
    ConceptStatus,
    GoalStatus,
    ReviewStatus,
    SessionMode,
    SessionStatus,
    TargetLevel,
)
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import (
    SqlConceptRepository,
    SqlGoalRepository,
    SqlReviewRepository,
    SqlSessionRepository,
)
from app.services.context_builder import GoalNotFoundError
from app.services.progress_service import ProgressService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _seed_goal(engine: Engine) -> None:
    SqlGoalRepository(engine).add(
        LearningGoal(
            id="goal_1",
            title="Learn SQL",
            target_level=TargetLevel.PROFESSIONAL,
            status=GoalStatus.ACTIVE,
            priority=3,
            created_at=NOW,
            updated_at=NOW,
        )
    )


def _seed_concept(engine: Engine, concept_id: str, **overrides: object) -> None:
    concepts = SqlConceptRepository(engine)
    defaults: dict[str, object] = dict(
        id=concept_id,
        title=concept_id,
        domain="sql",
        status=ConceptStatus.LEARNING,
        mastery=1.0,
        confidence=20,
        importance=3,
        retention=10,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    concepts.add(Concept(**defaults))  # type: ignore[arg-type]
    concepts.link_to_goal("goal_1", concept_id)


def _service(engine: Engine) -> ProgressService:
    return ProgressService(
        goals=SqlGoalRepository(engine),
        concepts=SqlConceptRepository(engine),
        reviews=SqlReviewRepository(engine),
        sessions=SqlSessionRepository(engine),
        clock=FakeClock(),
    )


def test_get_progress_raises_when_goal_missing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    with pytest.raises(GoalNotFoundError):
        _service(engine).get_progress("missing")


def test_get_progress_with_no_concepts_returns_zeros(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)

    progress = _service(engine).get_progress("goal_1")

    assert progress.mastery == 0.0
    assert progress.concepts_total == 0
    assert progress.mastered == 0
    assert progress.weak == 0
    assert progress.due_reviews == 0
    assert progress.recent_sessions == 0


def test_get_progress_averages_and_normalizes_mastery(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    _seed_concept(engine, "a", mastery=5.0, status=ConceptStatus.MASTERED)
    _seed_concept(engine, "b", mastery=0.0, status=ConceptStatus.WEAK)

    progress = _service(engine).get_progress("goal_1")

    assert progress.concepts_total == 2
    assert progress.mastery == 0.5
    assert progress.mastered == 1
    assert progress.weak == 1


def test_get_progress_counts_due_reviews_for_this_goal_only(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    _seed_concept(engine, "a")
    SqlGoalRepository(engine).add(
        LearningGoal(
            id="other_goal",
            title="Learn Python",
            target_level=TargetLevel.PROFESSIONAL,
            status=GoalStatus.ACTIVE,
            priority=3,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    reviews = SqlReviewRepository(engine)
    reviews.add(
        Review(
            id="review_1",
            concept_id="a",
            goal_id="goal_1",
            scheduled_at=NOW - timedelta(hours=1),
            interval_days=4.0,
            status=ReviewStatus.SCHEDULED,
        )
    )
    reviews.add(
        Review(
            id="review_2",
            concept_id="a",
            goal_id="other_goal",
            scheduled_at=NOW - timedelta(hours=1),
            interval_days=4.0,
            status=ReviewStatus.SCHEDULED,
        )
    )

    progress = _service(engine).get_progress("goal_1")

    assert progress.due_reviews == 1


def test_get_progress_counts_only_recent_sessions(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    sessions = SqlSessionRepository(engine)
    sessions.add(
        Session(
            id="session_recent",
            goal_id="goal_1",
            mode=SessionMode.GUIDED,
            objective="Practice",
            status=SessionStatus.COMPLETED,
            started_at=NOW - timedelta(days=1),
        )
    )
    sessions.add(
        Session(
            id="session_old",
            goal_id="goal_1",
            mode=SessionMode.GUIDED,
            objective="Practice",
            status=SessionStatus.COMPLETED,
            started_at=NOW - timedelta(days=30),
        )
    )

    progress = _service(engine).get_progress("goal_1")

    assert progress.recent_sessions == 1
