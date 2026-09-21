"""Goal progress summary (docs/TASKS.md T107, docs/API_SPEC.md #10:
`GET /goals/{goal_id}/progress`).

Pure aggregation over already-materialized state -- no live mastery
recomputation here, same "read-only, no compute" split T100's
`KnowledgeExplorerService` already established for concept listing.

`mastery` in the response is normalized to 0..1 (the spec's own example
shows `0.62`) -- `Concept.mastery` itself is a 0..5 scale
(docs/DOMAIN_MODEL.md #18), so the goal-level average is divided by
`MAX_MASTERY` here. Not stated anywhere else; a judgment call reading
the spec's example as a fraction, consistent with every other
client-facing percentage/fraction in the API (confidence, retention).

`due_reviews` filters `ReviewRepository.list_due(now)` (T063,
goal-agnostic -- the same call `TodaysReviewsService`/T086 already makes
unscoped) down to this goal in-memory rather than adding a new
goal-scoped repository query -- `Review` already carries `goal_id`
(docs/DOMAIN_MODEL.md #11), so no schema/port change is needed for it.

`recent_sessions` counts this goal's sessions started within the last
`RECENT_SESSIONS_WINDOW_DAYS` -- API_SPEC.md gives no definition of
"recent" anywhere, so a one-week window is chosen as the most natural
MVP reading for a spaced-repetition learning app; no other doc defines
one. This needed a real port-level gap fix: `SessionRepository` never
had any way to list a goal's sessions at all (only `add`/`get`/
`update`) -- added `list_by_goal` to the port and `SqlSessionRepository`,
same kind of gap fix earlier tasks made when an aggregate needed a
query that didn't exist yet (T068's `RoadmapRepository`, T092's
`ProjectRepository`).
"""

from dataclasses import dataclass
from datetime import timedelta

from app.domain.enums import ConceptStatus
from app.domain.ports import (
    ClockPort,
    ConceptRepository,
    GoalRepository,
    ReviewRepository,
    SessionRepository,
)
from app.services.context_builder import GoalNotFoundError

__all__ = ["GoalNotFoundError", "GoalProgress", "ProgressService"]

MAX_MASTERY = 5.0
RECENT_SESSIONS_WINDOW_DAYS = 7


@dataclass(frozen=True)
class GoalProgress:
    mastery: float
    concepts_total: int
    mastered: int
    weak: int
    due_reviews: int
    recent_sessions: int


class ProgressService:
    def __init__(
        self,
        goals: GoalRepository,
        concepts: ConceptRepository,
        reviews: ReviewRepository,
        sessions: SessionRepository,
        clock: ClockPort,
    ) -> None:
        self._goals = goals
        self._concepts = concepts
        self._reviews = reviews
        self._sessions = sessions
        self._clock = clock

    def get_progress(self, goal_id: str) -> GoalProgress:
        if self._goals.get(goal_id) is None:
            raise GoalNotFoundError(goal_id)

        now = self._clock.now()
        concepts = self._concepts.list_by_goal(goal_id)
        concepts_total = len(concepts)
        mastery = (
            sum(c.mastery for c in concepts) / concepts_total / MAX_MASTERY
            if concepts_total
            else 0.0
        )
        mastered = sum(1 for c in concepts if c.status == ConceptStatus.MASTERED)
        weak = sum(1 for c in concepts if c.status == ConceptStatus.WEAK)

        due_reviews = sum(1 for r in self._reviews.list_due(now) if r.goal_id == goal_id)

        window_start = now - timedelta(days=RECENT_SESSIONS_WINDOW_DAYS)
        recent_sessions = sum(
            1
            for s in self._sessions.list_by_goal(goal_id)
            if s.started_at is not None and s.started_at >= window_start
        )

        return GoalProgress(
            mastery=round(mastery, 2),
            concepts_total=concepts_total,
            mastered=mastered,
            weak=weak,
            due_reviews=due_reviews,
            recent_sessions=recent_sessions,
        )
