"""Session application service -- creates a Session for a goal
(docs/TASKS.md T069, docs/API_SPEC.md #6: `POST /goals/{goal_id}/sessions`
takes `mode` + `duration_minutes`).

`duration_minutes` is accepted and validated here but is not itself a
persisted Session column -- docs/DATABASE_SCHEMA.md's `sessions` table
has none. It is planning input for T070 (next-activity selection),
which decides how much to schedule within that time budget; it is not
durable state of the session itself.

There is no separate "start session" step anywhere in docs/API_SPEC.md
or docs/TASKS.md's Phase 6 backlog -- creating a session starts it
immediately (`status=active`, `started_at=now`), matching the actual
flow: create -> next activity -> answer -> ... -> complete.
"""

from app.domain.entities import Session
from app.domain.enums import SessionMode, SessionStatus
from app.domain.ports import ClockPort, GoalRepository, IdGeneratorPort, SessionRepository
from app.services.context_builder import GoalNotFoundError
from app.services.next_activity_service import SessionNotFoundError

DEFAULT_OBJECTIVE_TEMPLATE = "Practice session for {goal_title}"


class InvalidSessionError(Exception):
    pass


class InvalidSessionTransitionError(Exception):
    pass


class SessionApplicationService:
    def __init__(
        self,
        goals: GoalRepository,
        sessions: SessionRepository,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._goals = goals
        self._sessions = sessions
        self._clock = clock
        self._ids = ids

    def create_session(
        self,
        goal_id: str,
        mode: SessionMode,
        duration_minutes: int,
        objective: str | None = None,
    ) -> Session:
        goal = self._goals.get(goal_id)
        if goal is None:
            raise GoalNotFoundError(goal_id)
        if duration_minutes <= 0:
            raise InvalidSessionError("duration_minutes must be positive")

        now = self._clock.now()
        session = Session(
            id=self._ids.new_id("session"),
            goal_id=goal_id,
            mode=mode,
            objective=objective or DEFAULT_OBJECTIVE_TEMPLATE.format(goal_title=goal.title),
            status=SessionStatus.ACTIVE,
            started_at=now,
        )
        self._sessions.add(session)
        return session

    def get_session(self, session_id: str) -> Session:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    def complete_session(self, session_id: str) -> Session:
        """Only `active -> completed` is valid (docs/DOMAIN_MODEL.md #17:
        "Invalid transitions must be rejected by the domain layer")."""
        session = self.get_session(session_id)
        if session.status != SessionStatus.ACTIVE:
            raise InvalidSessionTransitionError(
                f"cannot complete a session in status '{session.status}'"
            )
        completed = session.model_copy(
            update={"status": SessionStatus.COMPLETED, "ended_at": self._clock.now()}
        )
        self._sessions.update(completed)
        return completed
