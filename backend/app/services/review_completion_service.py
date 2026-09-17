"""Review completion -- answer, evaluate, and reschedule a due review
(docs/TASKS.md T087, docs/API_SPEC.md #7:
`POST /reviews/{review_id}/complete` takes `answer` + `confidence`).

A Review has no linked Exercise (docs/DOMAIN_MODEL.md #11: id,
concept_id, goal_id, scheduled_at, completed_at, interval_days,
stability, difficulty, status -- no exercise_id/prompt anywhere), so
completing one cannot reuse the Evaluator AI role (T073), which needs a
real exercise prompt/solution/success_criteria to grade against.
Completion is self-reported instead: `EvidenceSourceType.REVIEW` is its
own dedicated evidence source (docs/DOMAIN_MODEL.md #6), distinct from
`exercise`/`assessment` -- correctness is derived directly from the
user's own confidence in their recall, the same signal the request
already carries.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.entities import Evidence, Review
from app.domain.enums import EvidenceSourceType, ReviewStatus
from app.domain.ports import ClockPort, EvidenceRepository, IdGeneratorPort, ReviewRepository
from app.domain.value_objects import ConfidencePercent
from app.services.review_creation_service import ReviewCreationService

DEFAULT_REVIEW_DIFFICULTY = 3
"""Evidence.difficulty (1..5) has no natural source for a review -- a
Review's own `difficulty` field is the FSRS parameter (unused, always
None under the MVP scheduler, T063), a different scale entirely. A
fixed mid-scale default is a reasonable MVP choice absent any stored
exercise difficulty for reviews."""


class ReviewNotFoundError(Exception):
    pass


class ReviewNotDueError(Exception):
    pass


@dataclass(frozen=True)
class ReviewCompletionResult:
    completed_review: Review
    evidence: Evidence
    next_review: Review


class ReviewCompletionService:
    def __init__(
        self,
        reviews: ReviewRepository,
        evidence: EvidenceRepository,
        review_creation: ReviewCreationService,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._reviews = reviews
        self._evidence = evidence
        self._review_creation = review_creation
        self._clock = clock
        self._ids = ids

    def complete_review(
        self, review_id: str, activity_id: str, answer: str, confidence: ConfidencePercent
    ) -> ReviewCompletionResult:
        review = self._reviews.get(review_id)
        if review is None:
            raise ReviewNotFoundError(review_id)
        if review.status not in (ReviewStatus.SCHEDULED, ReviewStatus.OVERDUE):
            raise ReviewNotDueError(f"review {review_id} is {review.status.value}, not due")

        now: datetime = self._clock.now()
        correctness = confidence / 100

        completed = review.model_copy(
            update={"status": ReviewStatus.COMPLETED, "completed_at": now}
        )
        self._reviews.update(completed)

        record = Evidence(
            id=self._ids.new_id("evidence"),
            concept_id=review.concept_id,
            goal_id=review.goal_id,
            activity_id=activity_id,
            source_type=EvidenceSourceType.REVIEW,
            difficulty=DEFAULT_REVIEW_DIFFICULTY,
            correctness=correctness,
            timestamp=now,
            metadata={"answer": answer, "review_id": review_id},
        )
        self._evidence.add(record)

        next_review = self._review_creation.schedule_review(
            review.concept_id, review.goal_id, correctness
        )

        return ReviewCompletionResult(
            completed_review=completed, evidence=record, next_review=next_review
        )
