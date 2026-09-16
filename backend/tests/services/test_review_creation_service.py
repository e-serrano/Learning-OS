from datetime import UTC, datetime, timedelta

from app.domain.entities import Review
from app.domain.enums import ReviewStatus
from app.services.review_creation_service import ReviewCreationService
from app.services.review_scheduler import ReviewScheduler

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeReviewRepository:
    def __init__(self, reviews: list[Review] | None = None) -> None:
        self.added: list[Review] = list(reviews or [])

    def add(self, review: Review) -> None:
        self.added.append(review)

    def get(self, review_id: str) -> Review | None:
        return next((r for r in self.added if r.id == review_id), None)

    def list_due(self, before: datetime) -> list[Review]:
        return [r for r in self.added if r.scheduled_at <= before]

    def list_by_concept(self, concept_id: str) -> list[Review]:
        return [r for r in self.added if r.concept_id == concept_id]

    def update(self, review: Review) -> None:
        raise NotImplementedError


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


def _review(**overrides: object) -> Review:
    defaults: dict[str, object] = dict(
        id="review_old",
        concept_id="concept_1",
        goal_id="goal_1",
        scheduled_at=NOW - timedelta(days=10),
        completed_at=NOW - timedelta(days=9),
        interval_days=4.0,
        status=ReviewStatus.COMPLETED,
    )
    defaults.update(overrides)
    return Review(**defaults)  # type: ignore[arg-type]


def test_schedule_review_with_no_prior_review_uses_initial_interval() -> None:
    reviews = FakeReviewRepository()
    service = ReviewCreationService(reviews, ReviewScheduler(FakeClock(NOW), FakeIdGenerator()))

    review = service.schedule_review("concept_1", "goal_1", correctness=1.0)

    assert review.interval_days == 1.0
    assert reviews.added == [review]


def test_schedule_review_grows_interval_from_the_latest_completed_review() -> None:
    reviews = FakeReviewRepository([_review(interval_days=4.0)])
    service = ReviewCreationService(reviews, ReviewScheduler(FakeClock(NOW), FakeIdGenerator()))

    review = service.schedule_review("concept_1", "goal_1", correctness=0.9)

    assert review.interval_days == 8.0


def test_schedule_review_ignores_incomplete_reviews_as_previous() -> None:
    reviews = FakeReviewRepository(
        [_review(id="never_completed", completed_at=None, status=ReviewStatus.SCHEDULED)]
    )
    service = ReviewCreationService(reviews, ReviewScheduler(FakeClock(NOW), FakeIdGenerator()))

    review = service.schedule_review("concept_1", "goal_1", correctness=1.0)

    assert review.interval_days == 1.0  # treated as no prior review


def test_schedule_review_uses_the_most_recently_completed_review() -> None:
    reviews = FakeReviewRepository(
        [
            _review(id="older", completed_at=NOW - timedelta(days=20), interval_days=2.0),
            _review(id="newer", completed_at=NOW - timedelta(days=1), interval_days=10.0),
        ]
    )
    service = ReviewCreationService(reviews, ReviewScheduler(FakeClock(NOW), FakeIdGenerator()))

    review = service.schedule_review("concept_1", "goal_1", correctness=0.9)

    assert review.interval_days == 20.0  # 10.0 * GROWTH_FACTOR, not 2.0's


def test_schedule_review_only_considers_the_given_concept() -> None:
    reviews = FakeReviewRepository([_review(concept_id="other_concept", interval_days=50.0)])
    service = ReviewCreationService(reviews, ReviewScheduler(FakeClock(NOW), FakeIdGenerator()))

    review = service.schedule_review("concept_1", "goal_1", correctness=1.0)

    assert review.interval_days == 1.0
