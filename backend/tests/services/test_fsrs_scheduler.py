from datetime import UTC, datetime

from app.domain.entities import Review
from app.domain.enums import ReviewStatus
from app.services.fsrs_scheduler import (
    MAX_DIFFICULTY,
    MIN_DIFFICULTY,
    MIN_STABILITY,
    FsrsScheduler,
)
from app.services.review_scheduler import MAX_INTERVAL_DAYS, MIN_INTERVAL_DAYS, ReviewScheduler

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


def _review(
    interval_days: float, stability: float | None = None, difficulty: float | None = None
) -> Review:
    return Review(
        id="review_prev",
        concept_id="concept_1",
        goal_id="goal_1",
        scheduled_at=NOW,
        interval_days=interval_days,
        stability=stability,
        difficulty=difficulty,
        status=ReviewStatus.COMPLETED,
    )


def test_first_review_sets_stability_and_difficulty_within_bounds() -> None:
    scheduler = FsrsScheduler()

    result = scheduler.next_interval(previous=None, correctness=0.95)

    assert result.stability is not None and result.stability >= MIN_STABILITY
    assert result.difficulty is not None
    assert MIN_DIFFICULTY <= result.difficulty <= MAX_DIFFICULTY
    assert result.interval_days >= MIN_INTERVAL_DAYS


def test_a_review_with_no_stability_history_is_treated_as_a_first_review() -> None:
    scheduler = FsrsScheduler()
    mvp_previous = _review(interval_days=30.0)  # SimpleSpacedRepetitionScheduler never sets these

    result = scheduler.next_interval(previous=mvp_previous, correctness=0.95)
    fresh = scheduler.next_interval(previous=None, correctness=0.95)

    assert result.stability == fresh.stability
    assert result.difficulty == fresh.difficulty


def test_successful_recall_grows_stability_and_interval() -> None:
    scheduler = FsrsScheduler()
    previous = _review(interval_days=4.0, stability=4.0, difficulty=5.0)

    result = scheduler.next_interval(previous=previous, correctness=0.95)

    assert result.stability is not None and result.stability > previous.stability  # type: ignore[operator]
    assert result.interval_days > MIN_INTERVAL_DAYS


def test_failed_recall_shrinks_stability_relative_to_a_successful_one() -> None:
    scheduler = FsrsScheduler()
    previous = _review(interval_days=10.0, stability=10.0, difficulty=5.0)

    failed = scheduler.next_interval(previous=previous, correctness=0.1)
    succeeded = scheduler.next_interval(previous=previous, correctness=0.95)

    assert failed.stability is not None and succeeded.stability is not None
    assert failed.stability < succeeded.stability
    assert failed.interval_days < succeeded.interval_days


def test_higher_grades_yield_non_decreasing_stability() -> None:
    scheduler = FsrsScheduler()
    previous = _review(interval_days=6.0, stability=6.0, difficulty=5.0)

    again = scheduler.next_interval(previous=previous, correctness=0.1)
    hard = scheduler.next_interval(previous=previous, correctness=0.5)
    good = scheduler.next_interval(previous=previous, correctness=0.7)
    easy = scheduler.next_interval(previous=previous, correctness=0.95)

    stabilities = [again.stability, hard.stability, good.stability, easy.stability]
    assert all(s is not None for s in stabilities)
    assert stabilities == sorted(stabilities)  # type: ignore[type-var]


def test_interval_is_floored_at_the_minimum() -> None:
    scheduler = FsrsScheduler()
    previous = _review(interval_days=1.0, stability=MIN_STABILITY, difficulty=8.0)

    result = scheduler.next_interval(previous=previous, correctness=0.0)

    assert result.interval_days >= MIN_INTERVAL_DAYS


def test_interval_is_capped_at_the_maximum() -> None:
    scheduler = FsrsScheduler()
    previous = _review(interval_days=180.0, stability=500.0, difficulty=1.0)

    result = scheduler.next_interval(previous=previous, correctness=1.0)

    assert result.interval_days == MAX_INTERVAL_DAYS


def test_difficulty_stays_within_bounds_across_many_failures() -> None:
    scheduler = FsrsScheduler()
    previous = _review(interval_days=2.0, stability=2.0, difficulty=9.9)

    for _ in range(10):
        result = scheduler.next_interval(previous=previous, correctness=0.05)
        assert MIN_DIFFICULTY <= result.difficulty <= MAX_DIFFICULTY  # type: ignore[operator]
        previous = _review(
            interval_days=result.interval_days,
            stability=result.stability,
            difficulty=result.difficulty,
        )


def test_fsrs_scheduler_is_a_drop_in_strategy_for_review_scheduler() -> None:
    scheduler = ReviewScheduler(FakeClock(NOW), FakeIdGenerator(), strategy=FsrsScheduler())

    review = scheduler.schedule_next("concept_1", "goal_1", correctness=0.95, previous=None)

    assert review.stability is not None
    assert review.difficulty is not None
    assert review.status.value == "scheduled"
