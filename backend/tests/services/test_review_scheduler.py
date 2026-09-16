from datetime import UTC, datetime, timedelta

from app.domain.entities import Review
from app.domain.enums import ReviewStatus
from app.services.review_scheduler import (
    MAX_INTERVAL_DAYS,
    MIN_INTERVAL_DAYS,
    ReviewScheduler,
    SchedulingResult,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


def _previous_review(interval_days: float) -> Review:
    return Review(
        id="review_prev",
        concept_id="concept_1",
        goal_id="goal_1",
        scheduled_at=NOW,
        interval_days=interval_days,
        status=ReviewStatus.COMPLETED,
    )


def test_first_review_uses_the_initial_interval() -> None:
    scheduler = ReviewScheduler(FakeClock(NOW), FakeIdGenerator())

    review = scheduler.schedule_next("concept_1", "goal_1", correctness=1.0, previous=None)

    assert review.interval_days == 1.0
    assert review.scheduled_at == NOW + timedelta(days=1)
    assert review.status == ReviewStatus.SCHEDULED
    assert review.stability is None
    assert review.difficulty is None


def test_successful_recall_grows_the_interval_geometrically() -> None:
    scheduler = ReviewScheduler(FakeClock(NOW), FakeIdGenerator())

    review = scheduler.schedule_next(
        "concept_1", "goal_1", correctness=0.9, previous=_previous_review(4.0)
    )

    assert review.interval_days == 8.0


def test_success_threshold_boundary_counts_as_success() -> None:
    scheduler = ReviewScheduler(FakeClock(NOW), FakeIdGenerator())

    review = scheduler.schedule_next(
        "concept_1", "goal_1", correctness=0.6, previous=_previous_review(4.0)
    )

    assert review.interval_days == 8.0


def test_failed_recall_resets_to_the_floor() -> None:
    scheduler = ReviewScheduler(FakeClock(NOW), FakeIdGenerator())

    review = scheduler.schedule_next(
        "concept_1", "goal_1", correctness=0.3, previous=_previous_review(30.0)
    )

    assert review.interval_days == MIN_INTERVAL_DAYS


def test_interval_is_capped_at_the_maximum() -> None:
    scheduler = ReviewScheduler(FakeClock(NOW), FakeIdGenerator())

    review = scheduler.schedule_next(
        "concept_1", "goal_1", correctness=1.0, previous=_previous_review(150.0)
    )

    assert review.interval_days == MAX_INTERVAL_DAYS


def test_custom_strategy_is_used_ready_for_fsrs_style_swap() -> None:
    class FakeFsrsLikeStrategy:
        def next_interval(self, previous: Review | None, correctness: float) -> SchedulingResult:
            return SchedulingResult(interval_days=42.0, stability=7.5, difficulty=3.2)

    scheduler = ReviewScheduler(FakeClock(NOW), FakeIdGenerator(), strategy=FakeFsrsLikeStrategy())

    review = scheduler.schedule_next("concept_1", "goal_1", correctness=1.0, previous=None)

    assert review.interval_days == 42.0
    assert review.stability == 7.5
    assert review.difficulty == 3.2


def test_new_review_gets_a_generated_id_and_scheduled_status() -> None:
    scheduler = ReviewScheduler(FakeClock(NOW), FakeIdGenerator())

    review = scheduler.schedule_next("concept_1", "goal_1", correctness=1.0, previous=None)

    assert review.id == "review_1"
    assert review.status == ReviewStatus.SCHEDULED
    assert review.completed_at is None
