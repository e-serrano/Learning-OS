"""Attaches real exercise content to a picked Activity (docs/TASKS.md
T103, docs/API_SPEC.md #6: `POST /sessions/{id}/next`'s `"content"`
field).

`NextActivityService`/`AdaptiveActivityService` (T070/T078) only ever
pick a bare `Activity` -- concept references, no prompt/question text.
Turning that into content the client can render means generating a real
`Exercise` (T071) for the activity's concept, then persisting the
pairing back onto `Activity.exercise_id` (docs/DOMAIN_MODEL.md #13 --
added in this same task) so a later `POST .../answer` call can find it.

Shared by the `/next` route and the answer route's embedded
`next_activity` (after `AdaptiveActivityService` re-ranks) -- both need
the exact same "pick -> generate -> remember the pairing" step.
"""

from dataclasses import dataclass

from app.domain.entities import Activity, Exercise
from app.domain.ports import ActivityRepository
from app.services.exercise_generator_service import ExerciseGeneratorService


@dataclass(frozen=True)
class ActivityContent:
    activity: Activity
    exercise: Exercise


class ActivityContentService:
    def __init__(
        self, activities: ActivityRepository, exercise_generator: ExerciseGeneratorService
    ) -> None:
        self._activities = activities
        self._exercise_generator = exercise_generator

    async def attach_exercise(self, goal_id: str, activity: Activity) -> ActivityContent:
        concept_id = activity.concept_ids[0]
        exercise = await self._exercise_generator.generate(goal_id, concept_id)
        updated = activity.model_copy(update={"exercise_id": exercise.id})
        self._activities.update(updated)
        return ActivityContent(activity=updated, exercise=exercise)
