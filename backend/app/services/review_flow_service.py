"""Full review-completion pipeline (docs/TASKS.md T104, docs/API_SPEC.md
#7: `POST /reviews/{review_id}/complete` takes only `answer` +
`confidence` -- no `activity_id`).

Two gaps closed here, both already flagged by earlier tasks' own notes
but left for "whichever route calls this":

1. `ReviewCompletionService.complete_review` (T087) requires a real
   `activity_id`, but `evidence.activity_id` is a NOT NULL FK to
   `activities`, which itself has a NOT NULL FK to `sessions`
   (docs/DATABASE_SCHEMA.md) -- and a standalone review (reached via
   `/reviews/*`, not nested under a `/sessions/*` route) has neither.
   `SessionMode.REVIEW`/`ActivityType.REVIEW` already exist for exactly
   this case, so this creates a minimal Session+Activity pair, both
   already `completed`, purely to satisfy the FK -- same precedent as
   T102's diagnostic session, but single-shot rather than multi-turn.
   The Session+Activity must be persisted *before* `complete_review`
   runs, since it is what writes the Evidence row the FK points at.
2. T088's own note: "`MasteryEngine` already reads `Concept.retention`
   ... but nothing wrote it until now" -- it built the write, not the
   caller. This is that caller, mirroring what `AnswerFlowService`
   (T103) already does for exercise evidence: update mastery and (here,
   review-specific) retention right after the evidence that feeds them
   is created. Retention is updated before mastery since
   `MasteryEngine` reads `Concept.retention` as one of its inputs --
   this way it sees the freshest value.
"""

from dataclasses import dataclass

from app.domain.entities import Activity, Concept, Evidence, Review, Session
from app.domain.enums import ActivityStatus, ActivityType, SessionMode, SessionStatus
from app.domain.ports import (
    ActivityRepository,
    ClockPort,
    IdGeneratorPort,
    ReviewRepository,
    SessionRepository,
)
from app.domain.value_objects import ConfidencePercent
from app.services.mastery_update_service import MasteryUpdateService
from app.services.retention_update_service import RetentionUpdateService
from app.services.review_completion_service import ReviewCompletionService, ReviewNotFoundError

__all__ = ["ReviewFlowResult", "ReviewFlowService", "ReviewNotFoundError"]


@dataclass(frozen=True)
class ReviewFlowResult:
    completed_review: Review
    evidence: Evidence
    next_review: Review
    concept: Concept


class ReviewFlowService:
    def __init__(
        self,
        reviews: ReviewRepository,
        sessions: SessionRepository,
        activities: ActivityRepository,
        review_completion: ReviewCompletionService,
        mastery_update: MasteryUpdateService,
        retention_update: RetentionUpdateService,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._reviews = reviews
        self._sessions = sessions
        self._activities = activities
        self._review_completion = review_completion
        self._mastery_update = mastery_update
        self._retention_update = retention_update
        self._clock = clock
        self._ids = ids

    def complete_review(
        self, review_id: str, answer: str, confidence: ConfidencePercent
    ) -> ReviewFlowResult:
        review = self._reviews.get(review_id)
        if review is None:
            raise ReviewNotFoundError(review_id)

        now = self._clock.now()
        session = Session(
            id=self._ids.new_id("session"),
            goal_id=review.goal_id,
            mode=SessionMode.REVIEW,
            objective="Spaced repetition review",
            status=SessionStatus.COMPLETED,
            started_at=now,
            ended_at=now,
        )
        self._sessions.add(session)
        activity = Activity(
            id=self._ids.new_id("activity"),
            session_id=session.id,
            type=ActivityType.REVIEW,
            sequence=1,
            concept_ids=[review.concept_id],
            status=ActivityStatus.COMPLETED,
        )
        self._activities.add(activity)

        result = self._review_completion.complete_review(review_id, activity.id, answer, confidence)

        self._retention_update.update_retention(result.evidence.concept_id)
        concept = self._mastery_update.update_mastery(result.evidence.concept_id)

        return ReviewFlowResult(
            completed_review=result.completed_review,
            evidence=result.evidence,
            next_review=result.next_review,
            concept=concept,
        )
