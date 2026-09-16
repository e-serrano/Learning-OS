"""Adaptive next activity -- re-ranks and picks the next activity
mid-session, after the mastery/mistake/review signals from the last
answer have just been updated (docs/TASKS.md T078; depends on T075-T077
having already written that fresh state).

Unlike T070's first-pass pick, this:
  (a) avoids immediately repeating the concept just worked on, when
      another candidate exists -- one answer rarely moves mastery enough
      to change the ranking, so a naive re-rank would otherwise pick the
      same concept over and over;
  (b) returns the full ranking reason (`ActivityCandidate`, with its
      per-factor breakdown from T064) alongside the persisted Activity,
      so the selection stays explainable rather than an opaque pick.
"""

from dataclasses import dataclass

from app.domain.entities import Activity
from app.domain.enums import SessionStatus
from app.domain.ports import ActivityRepository, IdGeneratorPort, SessionRepository
from app.services.activity_selector import ActivityCandidate, ActivitySelector
from app.services.next_activity_service import (
    InactiveSessionError,
    NoActivityCandidatesError,
    SessionNotFoundError,
    create_and_persist_activity,
)


@dataclass(frozen=True)
class AdaptiveActivityResult:
    activity: Activity
    reason: ActivityCandidate


class AdaptiveActivityService:
    def __init__(
        self,
        sessions: SessionRepository,
        activities: ActivityRepository,
        activity_selector: ActivitySelector,
        ids: IdGeneratorPort,
    ) -> None:
        self._sessions = sessions
        self._activities = activities
        self._activity_selector = activity_selector
        self._ids = ids

    def select_next(
        self, session_id: str, just_completed_concept_id: str | None = None
    ) -> AdaptiveActivityResult:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        if session.status != SessionStatus.ACTIVE:
            raise InactiveSessionError(session_id)

        ranked = self._activity_selector.rank(session.goal_id)
        if not ranked:
            raise NoActivityCandidatesError(session.goal_id)

        chosen = self._choose(ranked, just_completed_concept_id)
        activity = create_and_persist_activity(
            self._activities, self._ids, session_id, chosen.concept_id
        )
        return AdaptiveActivityResult(activity=activity, reason=chosen)

    def _choose(
        self,
        ranked: list[ActivityCandidate],
        just_completed_concept_id: str | None,
    ) -> ActivityCandidate:
        if just_completed_concept_id is None:
            return ranked[0]
        for candidate in ranked:
            if candidate.concept_id != just_completed_concept_id:
                return candidate
        return ranked[0]  # every candidate is the one just completed
