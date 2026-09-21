"""Assessment session creation/lookup (docs/TASKS.md T105,
docs/API_SPEC.md #8: `POST /goals/{goal_id}/assessments`,
`GET /assessments/{assessment_id}`).

Same FK-scaffolding gap as T102's diagnostic and T104's review: a
transfer assessment (T089) is just a generated Exercise, and grading it
(T090's `AssessmentCompletionService`) writes Evidence whose
`activity_id` is a NOT NULL FK through `activities` to `sessions`. A
`POST /goals/{goal_id}/assessments` request has neither, so this
creates a real Session (`mode=assessment`) + Activity
(`type=assessment`) pair here, before generating the exercise content
persists anything durable to point at.

Unlike T102/T104's scaffolding, this Session is left `active` rather
than pre-completed: an assessment is answered (T090, unchanged) and
then explicitly closed via `POST /assessments/{id}/complete`, which
reuses `SessionApplicationService.complete_session` -- the same
"answer = full grade, complete = close session" split T103 established
for regular sessions and T104 cited as precedent.

`assessment_id` in the URL is the Activity's id, not a new identifier
-- mirrors T103/T104's precedent of the Activity being the addressable
unit for a piece of session content.
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
from app.services.transfer_assessment_service import TransferAssessmentService

__all__ = [
    "AssessmentNotFoundError",
    "ActivityNotAnAssessmentError",
    "AssessmentSessionResult",
    "AssessmentSessionService",
]


class AssessmentNotFoundError(Exception):
    pass


class ActivityNotAnAssessmentError(Exception):
    pass


@dataclass(frozen=True)
class AssessmentSessionResult:
    session: Session
    activity: Activity
    exercise: Exercise


class AssessmentSessionService:
    def __init__(
        self,
        sessions: SessionRepository,
        activities: ActivityRepository,
        exercises: ExerciseRepository,
        transfer_assessment: TransferAssessmentService,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._sessions = sessions
        self._activities = activities
        self._exercises = exercises
        self._transfer_assessment = transfer_assessment
        self._clock = clock
        self._ids = ids

    async def create_assessment(self, goal_id: str, concept_id: str) -> AssessmentSessionResult:
        exercise = await self._transfer_assessment.generate_transfer_scenario(goal_id, concept_id)

        now = self._clock.now()
        session = Session(
            id=self._ids.new_id("session"),
            goal_id=goal_id,
            mode=SessionMode.ASSESSMENT,
            objective=f"Transfer assessment for {concept_id}",
            status=SessionStatus.ACTIVE,
            started_at=now,
        )
        self._sessions.add(session)

        activity = Activity(
            id=self._ids.new_id("activity"),
            session_id=session.id,
            type=ActivityType.ASSESSMENT,
            sequence=1,
            concept_ids=[concept_id],
            status=ActivityStatus.ACTIVE,
            exercise_id=exercise.id,
        )
        self._activities.add(activity)

        return AssessmentSessionResult(session=session, activity=activity, exercise=exercise)

    def get_assessment(self, assessment_id: str) -> AssessmentSessionResult:
        activity = self._activities.get(assessment_id)
        if activity is None:
            raise AssessmentNotFoundError(assessment_id)
        if activity.type != ActivityType.ASSESSMENT:
            raise ActivityNotAnAssessmentError(assessment_id)

        session = self._sessions.get(activity.session_id)
        assert session is not None

        assert activity.exercise_id is not None
        exercise = self._exercises.get(activity.exercise_id)
        assert exercise is not None

        return AssessmentSessionResult(session=session, activity=activity, exercise=exercise)
