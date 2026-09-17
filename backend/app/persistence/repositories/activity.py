import json

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import Activity
from app.persistence.models import ActivityModel
from app.persistence.repositories._util import now_iso


def _to_model(activity: Activity, created_at: str) -> ActivityModel:
    return ActivityModel(
        id=activity.id,
        session_id=activity.session_id,
        type=activity.type.value,
        sequence=activity.sequence,
        status=activity.status.value,
        payload_json=json.dumps(
            {"concept_ids": activity.concept_ids, "exercise_id": activity.exercise_id}
        ),
        created_at=created_at,
    )


def _to_entity(model: ActivityModel) -> Activity:
    payload = json.loads(model.payload_json)
    return Activity(
        id=model.id,
        session_id=model.session_id,
        type=model.type,  # type: ignore[arg-type]
        sequence=model.sequence,
        concept_ids=payload.get("concept_ids", []),
        status=model.status,  # type: ignore[arg-type]
        exercise_id=payload.get("exercise_id"),
    )


class SqlActivityRepository:
    """Implements app.domain.ports.ActivityRepository against activities
    (T033 table, T070 port/adapter).

    `concept_ids` packs into `payload_json` because the schema has no
    dedicated column for it, matching how SqlExerciseRepository packs its
    own extra fields (docs/TASKS.md T035 note). `created_at` is a DB-only
    bookkeeping column not present on the Activity domain entity.

    `exercise_id` packs into the same `payload_json` blob (T103) -- an
    `exercise`-type Activity has no other way to remember which
    AI-generated Exercise it was paired with once `/next` hands it back
    to the caller; `POST .../activities/{id}/answer` needs it to call
    `AnswerSubmissionService`, which takes `exercise_id`, not
    `activity_id`.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, activity: Activity) -> None:
        with DbSession(self._engine) as db:
            db.add(_to_model(activity, created_at=now_iso()))
            db.commit()

    def get(self, activity_id: str) -> Activity | None:
        with DbSession(self._engine) as db:
            model = db.get(ActivityModel, activity_id)
            return _to_entity(model) if model is not None else None

    def list_by_session(self, session_id: str) -> list[Activity]:
        with DbSession(self._engine) as db:
            stmt = (
                select(ActivityModel)
                .where(ActivityModel.session_id == session_id)
                .order_by(ActivityModel.sequence)
            )
            return [_to_entity(m) for m in db.scalars(stmt)]

    def update(self, activity: Activity) -> None:
        with DbSession(self._engine) as db:
            existing = db.get(ActivityModel, activity.id)
            created_at = existing.created_at if existing is not None else now_iso()
            db.merge(_to_model(activity, created_at=created_at))
            db.commit()
