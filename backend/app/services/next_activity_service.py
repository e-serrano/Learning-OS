"""Next-activity service -- picks the highest-priority concept for a
session's goal (T064 `ActivitySelector`) and persists it as the
session's next `Activity` (docs/TASKS.md T070).

This is the session's *first-pass* activity pick. After each answer is
evaluated, T078 (adaptive next activity) re-ranks using the freshly
updated mastery/mistake/review signals from that answer -- this service
does not attempt that adaptivity itself, it only kicks off a session.
"""

from app.domain.entities import Activity
from app.domain.enums import ActivityStatus, ActivityType, SessionStatus
from app.domain.ports import ActivityRepository, IdGeneratorPort, SessionRepository
from app.services.activity_selector import ActivitySelector


class SessionNotFoundError(Exception):
    pass


class InactiveSessionError(Exception):
    pass


class NoActivityCandidatesError(Exception):
    pass


class NextActivityService:
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

    def select_next(self, session_id: str) -> Activity:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        if session.status != SessionStatus.ACTIVE:
            raise InactiveSessionError(session_id)

        ranked = self._activity_selector.rank(session.goal_id)
        if not ranked:
            raise NoActivityCandidatesError(session.goal_id)
        top_concept_id = ranked[0].concept_id

        sequence = len(self._activities.list_by_session(session_id)) + 1
        activity = Activity(
            id=self._ids.new_id("activity"),
            session_id=session_id,
            type=ActivityType.EXERCISE,
            sequence=sequence,
            concept_ids=[top_concept_id],
            status=ActivityStatus.ACTIVE,
        )
        self._activities.add(activity)
        return activity
