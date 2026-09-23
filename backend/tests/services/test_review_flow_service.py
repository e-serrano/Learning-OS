from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.domain.entities import Concept, LearningGoal, Review
from app.domain.enums import ConceptStatus, GoalStatus, ReviewStatus, TargetLevel
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import (
    SqlActivityRepository,
    SqlConceptRepository,
    SqlEvidenceRepository,
    SqlGoalRepository,
    SqlReviewRepository,
    SqlSessionRepository,
)
from app.services.mastery_engine import MasteryEngine
from app.services.mastery_update_service import MasteryUpdateService
from app.services.retention_update_service import RetentionUpdateService
from app.services.review_completion_service import ReviewCompletionService, ReviewNotFoundError
from app.services.review_creation_service import ReviewCreationService
from app.services.review_flow_service import ReviewFlowService
from app.services.review_scheduler import ReviewScheduler

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class FakeIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _seed_goal_and_concept(engine: Engine) -> None:
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
    SqlConceptRepository(engine).add(
        Concept(
            id="window_functions",
            title="Window Functions",
            domain="sql",
            status=ConceptStatus.LEARNING,
            mastery=1,
            confidence=20,
            importance=3,
            retention=10,
            created_at=NOW,
            updated_at=NOW,
        )
    )


def _seed_review(engine: Engine, **overrides: object) -> Review:
    defaults: dict[str, object] = dict(
        id="review_seed",
        concept_id="window_functions",
        goal_id="goal_1",
        scheduled_at=NOW - timedelta(hours=1),
        interval_days=4.0,
        status=ReviewStatus.SCHEDULED,
    )
    defaults.update(overrides)
    review = Review(**defaults)  # type: ignore[arg-type]
    SqlReviewRepository(engine).add(review)
    return review


def _service(engine: Engine) -> ReviewFlowService:
    reviews = SqlReviewRepository(engine)
    sessions = SqlSessionRepository(engine)
    activities = SqlActivityRepository(engine)
    evidence = SqlEvidenceRepository(engine)
    concepts = SqlConceptRepository(engine)

    review_creation = ReviewCreationService(
        reviews, ReviewScheduler(FakeClock(), FakeIdGenerator())
    )
    review_completion = ReviewCompletionService(
        reviews, evidence, review_creation, FakeClock(), FakeIdGenerator()
    )
    mastery_update = MasteryUpdateService(concepts, MasteryEngine(evidence))
    retention_update = RetentionUpdateService(concepts, evidence)

    return ReviewFlowService(
        reviews=reviews,
        sessions=sessions,
        activities=activities,
        review_completion=review_completion,
        mastery_update=mastery_update,
        retention_update=retention_update,
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )


@pytest.mark.asyncio
async def test_complete_review_creates_a_supporting_session_and_activity(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    _seed_review(engine)

    result = await _service(engine).complete_review(
        "review_seed", answer="ROW_NUMBER", confidence=80
    )

    assert result.completed_review.status == ReviewStatus.COMPLETED
    activity = SqlActivityRepository(engine).get(result.evidence.activity_id)
    assert activity is not None
    assert activity.concept_ids == ["window_functions"]
    session = SqlSessionRepository(engine).get(activity.session_id)
    assert session is not None
    assert session.goal_id == "goal_1"
    assert session.status.value == "completed"


@pytest.mark.asyncio
async def test_complete_review_updates_retention_and_mastery(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    _seed_review(engine)

    result = await _service(engine).complete_review(
        "review_seed", answer="ROW_NUMBER", confidence=90
    )

    assert result.concept.retention == 90.0
    stored = SqlConceptRepository(engine).get("window_functions")
    assert stored is not None
    assert stored.retention == 90.0


@pytest.mark.asyncio
async def test_complete_review_schedules_next_review(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    _seed_review(engine)

    result = await _service(engine).complete_review("review_seed", answer="x", confidence=80)

    assert result.next_review.id != "review_seed"
    assert result.next_review.scheduled_at > result.completed_review.completed_at  # type: ignore[operator]


@pytest.mark.asyncio
async def test_complete_review_raises_when_missing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)

    with pytest.raises(ReviewNotFoundError):
        await _service(engine).complete_review("missing", answer="x", confidence=50)
