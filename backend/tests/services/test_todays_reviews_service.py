from datetime import UTC, datetime, timedelta

from app.domain.entities import Review
from app.domain.enums import ReviewStatus
from app.services.todays_reviews_service import TodaysReviewsService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeReviewRepository:
    def __init__(self, reviews: list[Review]) -> None:
        self._reviews = reviews

    def list_due(self, before: datetime) -> list[Review]:
        return [r for r in self._reviews if r.scheduled_at <= before]


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def _review(**overrides: object) -> Review:
    defaults: dict[str, object] = dict(
        id="review_1",
        concept_id="concept_1",
        goal_id="goal_1",
        scheduled_at=NOW - timedelta(hours=1),
        interval_days=3.0,
        status=ReviewStatus.SCHEDULED,
    )
    defaults.update(overrides)
    return Review(**defaults)  # type: ignore[arg-type]


def test_list_today_includes_scheduled_reviews_due_now() -> None:
    service = TodaysReviewsService(FakeReviewRepository([_review()]), FakeClock(NOW))

    assert [r.id for r in service.list_today()] == ["review_1"]


def test_list_today_includes_overdue_reviews() -> None:
    service = TodaysReviewsService(
        FakeReviewRepository([_review(status=ReviewStatus.OVERDUE)]), FakeClock(NOW)
    )

    assert [r.id for r in service.list_today()] == ["review_1"]


def test_list_today_excludes_completed_reviews_even_if_scheduled_at_passed() -> None:
    service = TodaysReviewsService(
        FakeReviewRepository([_review(status=ReviewStatus.COMPLETED, completed_at=NOW)]),
        FakeClock(NOW),
    )

    assert service.list_today() == []


def test_list_today_excludes_skipped_reviews_even_if_scheduled_at_passed() -> None:
    service = TodaysReviewsService(
        FakeReviewRepository([_review(status=ReviewStatus.SKIPPED)]), FakeClock(NOW)
    )

    assert service.list_today() == []


def test_list_today_excludes_reviews_scheduled_in_the_future() -> None:
    service = TodaysReviewsService(
        FakeReviewRepository([_review(scheduled_at=NOW + timedelta(days=1))]), FakeClock(NOW)
    )

    assert service.list_today() == []


def test_list_today_uses_the_clock_as_the_cutoff() -> None:
    review = _review(scheduled_at=NOW + timedelta(hours=1))
    service = TodaysReviewsService(FakeReviewRepository([review]), FakeClock(NOW))
    assert service.list_today() == []

    later_service = TodaysReviewsService(
        FakeReviewRepository([review]), FakeClock(NOW + timedelta(hours=2))
    )
    assert [r.id for r in later_service.list_today()] == ["review_1"]
