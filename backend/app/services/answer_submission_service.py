"""Answer submission -- persists an ExerciseAttempt with the user's
answer and confidence (docs/TASKS.md T072, docs/API_SPEC.md #6:
`POST /sessions/{session_id}/activities/{activity_id}/answer`
takes `answer` + `confidence`).

This only records the raw attempt; grading it is the Evaluator's job
(T073), never this service's.
"""

from app.domain.entities import ExerciseAttempt
from app.domain.enums import SessionStatus
from app.domain.ports import (
    ClockPort,
    ExerciseAttemptRepository,
    ExerciseRepository,
    IdGeneratorPort,
    SessionRepository,
)
from app.domain.value_objects import ConfidencePercent
from app.services.next_activity_service import InactiveSessionError, SessionNotFoundError


class ExerciseNotFoundError(Exception):
    pass


class AnswerSubmissionService:
    def __init__(
        self,
        exercises: ExerciseRepository,
        sessions: SessionRepository,
        attempts: ExerciseAttemptRepository,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._exercises = exercises
        self._sessions = sessions
        self._attempts = attempts
        self._clock = clock
        self._ids = ids

    def submit_answer(
        self,
        exercise_id: str,
        session_id: str,
        answer: str,
        confidence: ConfidencePercent,
    ) -> ExerciseAttempt:
        if self._exercises.get(exercise_id) is None:
            raise ExerciseNotFoundError(exercise_id)

        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        if session.status != SessionStatus.ACTIVE:
            raise InactiveSessionError(session_id)

        attempt = ExerciseAttempt(
            id=self._ids.new_id("attempt"),
            exercise_id=exercise_id,
            session_id=session_id,
            answer=answer,
            confidence=confidence,
            submitted_at=self._clock.now(),
        )
        self._attempts.add(attempt)
        return attempt
