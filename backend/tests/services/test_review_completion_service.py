from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entities import Evidence, Review
from app.domain.enums import EvidenceSourceType, ReviewStatus
from app.services.review_completion_service import (
    ReviewCompletionService,
    ReviewNotDueError,
    ReviewNotFoundError,
)
from app.services.review_creation_service import ReviewCreationService
from app.services.review_scheduler import ReviewScheduler

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeReviewRepository:
    def __init__(self, reviews: list[Review]) -> None:
        self._by_id = {r.id: r for r in reviews}

    def add(self, review: Review) -> None:
        self._by_id[review.id] = review

    def get(self, review_id: str) -> Review | None:
        return self._by_id.get(review_id)

    def list_due(self, before: datetime) -> list[Review]:
        return [r for r in self._by_id.values() if r.scheduled_at <= before]

    def list_by_concept(self, concept_id: str) -> list[Review]:
        return [r for r in self._by_id.values() if r.concept_id == concept_id]

    def update(self, review: Review) -> None:
        self._by_id[review.id] = review


class FakeEvidenceRepository:
    def __init__(self) -> None:
        self.added: list[Evidence] = []

    def add(self, evidence: Evidence) -> None:
        self.added.append(evidence)

    def list_by_concept(self, concept_id: str) -> list[Evidence]:
        return [e for e in self.added if e.concept_id == concept_id]

    def list_by_goal(self, goal_id: str) -> list[Evidence]:
        return [e for e in self.added if e.goal_id == goal_id]


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
        scheduled_at=NOW - timedelta(hours=1),
        interval_days=4.0,
        status=ReviewStatus.SCHEDULED,
    )
    defaults.update(overrides)
    return Review(**defaults)  # type: ignore[arg-type]


def _service(
    reviews: FakeReviewRepository,
) -> tuple[ReviewCompletionService, FakeEvidenceRepository]:
    evidence = FakeEvidenceRepository()
    review_creation = ReviewCreationService(
        reviews, ReviewScheduler(FakeClock(NOW), FakeIdGenerator())
    )
    service = ReviewCompletionService(
        reviews, evidence, review_creation, FakeClock(NOW), FakeIdGenerator()
    )
    return service, evidence


def test_complete_review_marks_the_review_completed() -> None:
    reviews = FakeReviewRepository([_review()])
    service, _ = _service(reviews)

    result = service.complete_review("review_old", "activity_1", "my answer", confidence=90)

    assert result.completed_review.status == ReviewStatus.COMPLETED
    assert result.completed_review.completed_at == NOW
    assert reviews.get("review_old").status == ReviewStatus.COMPLETED  # type: ignore[union-attr]


def test_complete_review_creates_self_reported_evidence() -> None:
    reviews = FakeReviewRepository([_review()])
    service, evidence = _service(reviews)

    result = service.complete_review("review_old", "activity_1", "my answer", confidence=80)

    assert result.evidence.source_type == EvidenceSourceType.REVIEW
    assert result.evidence.correctness == 0.8
    assert result.evidence.concept_id == "concept_1"
    assert result.evidence.goal_id == "goal_1"
    assert result.evidence.metadata == {"answer": "my answer", "review_id": "review_old"}
    assert evidence.added == [result.evidence]


def test_complete_review_schedules_the_next_review_growing_from_the_completed_one() -> None:
    reviews = FakeReviewRepository([_review(interval_days=4.0)])
    service, _ = _service(reviews)

    result = service.complete_review("review_old", "activity_1", "my answer", confidence=90)

    assert result.next_review.interval_days == 8.0  # 4.0 * GROWTH_FACTOR
    assert result.next_review.status == ReviewStatus.SCHEDULED
    assert result.next_review.id != "review_old"


def test_complete_review_with_low_confidence_resets_the_next_interval() -> None:
    reviews = FakeReviewRepository([_review(interval_days=30.0)])
    service, _ = _service(reviews)

    result = service.complete_review("review_old", "activity_1", "my answer", confidence=20)

    assert result.next_review.interval_days == 1.0  # MIN_INTERVAL_DAYS, correctness 0.2 < threshold


def test_complete_review_raises_when_review_not_found() -> None:
    service, evidence = _service(FakeReviewRepository([]))

    with pytest.raises(ReviewNotFoundError):
        service.complete_review("missing_review", "activity_1", "answer", confidence=50)

    assert evidence.added == []


@pytest.mark.parametrize("status", [ReviewStatus.COMPLETED, ReviewStatus.SKIPPED])
def test_complete_review_raises_when_review_is_not_due(status: ReviewStatus) -> None:
    reviews = FakeReviewRepository([_review(status=status)])
    service, evidence = _service(reviews)

    with pytest.raises(ReviewNotDueError):
        service.complete_review("review_old", "activity_1", "answer", confidence=50)

    assert evidence.added == []
