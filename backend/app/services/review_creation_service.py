"""Review creation -- schedules the next review for a concept after new
evidence (docs/TASKS.md T077).

Thin wiring, like T075/T076: finds the concept's most recently
*completed* Review (if any) as the `previous` input to `ReviewScheduler`
(T063), then persists the result. `correctness` is supplied by the
caller -- the same score the Evaluator (T073) already produced for this
pipeline step, avoiding a third independent
Evaluation -> ExerciseAttempt -> Exercise traversal (see T074, T076 for
the other two).
"""

from datetime import datetime
from typing import cast

from app.domain.entities import Review
from app.domain.ports import ReviewRepository
from app.services.review_scheduler import ReviewScheduler


class ReviewCreationService:
    def __init__(self, reviews: ReviewRepository, scheduler: ReviewScheduler) -> None:
        self._reviews = reviews
        self._scheduler = scheduler

    def schedule_review(self, concept_id: str, goal_id: str, correctness: float) -> Review:
        previous = self._latest_completed_review(concept_id)
        review = self._scheduler.schedule_next(concept_id, goal_id, correctness, previous=previous)
        self._reviews.add(review)
        return review

    def _latest_completed_review(self, concept_id: str) -> Review | None:
        completed = [
            r for r in self._reviews.list_by_concept(concept_id) if r.completed_at is not None
        ]
        if not completed:
            return None
        return max(completed, key=lambda r: cast(datetime, r.completed_at))
