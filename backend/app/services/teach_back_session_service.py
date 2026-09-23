"""Teach-back session creation/lookup (docs/TASKS.md T133,
docs/API_SPEC.md #6: `POST /goals/{goal_id}/teach-back`,
`GET /teach-back/{teach_back_id}`).

Sibling of `AssessmentSessionService` (T105): same FK-scaffolding need --
answering the generated Exercise writes Evidence whose `activity_id` is a
NOT NULL FK through `activities` to `sessions`, so this creates a real
Session (`mode=teach_back`) + Activity (`type=exercise`, the same type
every ordinary exercise activity uses -- `ActivityType` has no dedicated
teach-back value, and doesn't need one; `Exercise.type=TEACH_BACK` is
what actually distinguishes it) pair before generating content.

Unlike assessment mode, teach-back needs no dedicated completion
service/route: answering it produces a normal `Evaluation` and,
via `EvidenceCreationService`'s type-aware `source_type` (T133),
correctly-tagged `Evidence` -- the existing
`POST /sessions/{id}/activities/{id}/answer` (`AnswerFlowService`, T103)
and `POST /sessions/{id}/complete` handle it unchanged. Assessment mode's
extra completion layer exists only because it computes a thresholded
transfer/independence pass-fail judgment on top of a normal evaluation
(T090); teach-back has no equivalent extra judgment to compute.
"""

from dataclasses import dataclass

from app.domain.entities import Activity, Exercise, Session
from app.domain.enums import ActivityStatus, ActivityType, SessionMode, SessionStatus
from app.domain.ports import (
    ActivityRepository,
    ClockPort,
    ExerciseRepository,
    IdGeneratorPort,
    SessionRepository,
)
from app.services.teach_back_service import TeachBackService

__all__ = [
    "TeachBackNotFoundError",
    "ActivityNotATeachBackError",
    "TeachBackSessionResult",
    "TeachBackSessionService",
]


class TeachBackNotFoundError(Exception):
    pass


class ActivityNotATeachBackError(Exception):
    pass


@dataclass(frozen=True)
class TeachBackSessionResult:
    session: Session
    activity: Activity
    exercise: Exercise


class TeachBackSessionService:
    def __init__(
        self,
        sessions: SessionRepository,
        activities: ActivityRepository,
        exercises: ExerciseRepository,
        teach_back: TeachBackService,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._sessions = sessions
        self._activities = activities
        self._exercises = exercises
        self._teach_back = teach_back
        self._clock = clock
        self._ids = ids

    async def create_teach_back(self, goal_id: str, concept_id: str) -> TeachBackSessionResult:
        exercise = await self._teach_back.generate_teach_back(goal_id, concept_id)

        now = self._clock.now()
        session = Session(
            id=self._ids.new_id("session"),
            goal_id=goal_id,
            mode=SessionMode.TEACH_BACK,
            objective=f"Teach back {concept_id}",
            status=SessionStatus.ACTIVE,
            started_at=now,
        )
        self._sessions.add(session)

        activity = Activity(
            id=self._ids.new_id("activity"),
            session_id=session.id,
            type=ActivityType.EXERCISE,
            sequence=1,
            concept_ids=[concept_id],
            status=ActivityStatus.ACTIVE,
            exercise_id=exercise.id,
        )
        self._activities.add(activity)

        return TeachBackSessionResult(session=session, activity=activity, exercise=exercise)

    def get_teach_back(self, teach_back_id: str) -> TeachBackSessionResult:
        """`AssessmentSessionService.get_assessment` checks `activity.type
        != ActivityType.ASSESSMENT`; a teach-back Activity has no such
        dedicated marker (`type=EXERCISE`, same as any other exercise
        activity), so this checks the owning session's `mode` instead --
        `create_teach_back` always sets it, so the same identity check."""
        activity = self._activities.get(teach_back_id)
        if activity is None:
            raise TeachBackNotFoundError(teach_back_id)

        session = self._sessions.get(activity.session_id)
        if session is None or session.mode != SessionMode.TEACH_BACK:
            raise ActivityNotATeachBackError(teach_back_id)

        assert activity.exercise_id is not None
        exercise = self._exercises.get(activity.exercise_id)
        assert exercise is not None

        return TeachBackSessionResult(session=session, activity=activity, exercise=exercise)
