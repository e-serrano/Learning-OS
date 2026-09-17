"""Today's reviews -- query reviews due now (docs/TASKS.md T086,
docs/API_SPEC.md #7: `GET /reviews/today`).

`ReviewRepository.list_due(before)` (T035) filters only by
`scheduled_at`, not status -- a completed or skipped review whose
`scheduled_at` happens to be in the past would still match. This
service also filters to the two "not yet handled" statuses (scheduled,
overdue), so a completed/skipped review never shows up as still due.
"""

from app.domain.entities import Review
from app.domain.enums import ReviewStatus
from app.domain.ports import ClockPort, ReviewRepository

DUE_STATUSES = frozenset({ReviewStatus.SCHEDULED, ReviewStatus.OVERDUE})


class TodaysReviewsService:
    def __init__(self, reviews: ReviewRepository, clock: ClockPort) -> None:
        self._reviews = reviews
        self._clock = clock

    def list_today(self) -> list[Review]:
        due = self._reviews.list_due(self._clock.now())
        return [review for review in due if review.status in DUE_STATUSES]
