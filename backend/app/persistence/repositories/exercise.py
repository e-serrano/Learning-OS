import json

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import Exercise
from app.persistence.models import ExerciseConceptModel, ExerciseModel
from app.persistence.repositories._util import dt_to_str, str_to_dt


def _to_model(exercise: Exercise) -> ExerciseModel:
    metadata = {
        "skill_ids": exercise.skill_ids,
        "prerequisite_ids": exercise.prerequisite_ids,
        "success_criteria": exercise.success_criteria,
        "hints": exercise.hints,
        "common_mistakes": exercise.common_mistakes,
        "transfer_variant": exercise.transfer_variant,
    }
    return ExerciseModel(
        id=exercise.id,
        type=exercise.type.value,
        difficulty=exercise.difficulty,
        goal_id=exercise.goal_id,
        prompt=exercise.prompt,
        solution=exercise.solution,
        metadata_json=json.dumps(metadata),
        created_at=dt_to_str(exercise.created_at),
    )


def _to_entity(model: ExerciseModel, concept_ids: list[str]) -> Exercise:
    metadata = json.loads(model.metadata_json)
    return Exercise(
        id=model.id,
        type=model.type,  # type: ignore[arg-type]
        difficulty=model.difficulty,
        goal_id=model.goal_id,
        concept_ids=concept_ids,
        skill_ids=metadata.get("skill_ids", []),
        prerequisite_ids=metadata.get("prerequisite_ids", []),
        prompt=model.prompt,
        success_criteria=metadata.get("success_criteria", []),
        hints=metadata.get("hints", []),
        solution=model.solution,
        common_mistakes=metadata.get("common_mistakes", []),
        transfer_variant=metadata.get("transfer_variant"),
        created_at=str_to_dt(model.created_at),  # type: ignore[arg-type]
    )


class SqlExerciseRepository:
    """Implements app.domain.ports.ExerciseRepository against exercises (T033).

    concept_ids come from the exercise_concepts join table; the remaining
    list fields (skill_ids, prerequisite_ids, success_criteria, hints,
    common_mistakes, transfer_variant) are bundled into metadata_json, since
    DATABASE_SCHEMA.md has no dedicated columns for them.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def _concept_ids(self, db: DbSession, exercise_id: str) -> list[str]:
        stmt = select(ExerciseConceptModel.concept_id).where(
            ExerciseConceptModel.exercise_id == exercise_id
        )
        return list(db.scalars(stmt))

    def add(self, exercise: Exercise) -> None:
        with DbSession(self._engine) as db:
            db.add(_to_model(exercise))
            db.flush()  # exercise row must exist before exercise_concepts references it
            for concept_id in exercise.concept_ids:
                db.add(
                    ExerciseConceptModel(exercise_id=exercise.id, concept_id=concept_id)
                )
            db.commit()

    def get(self, exercise_id: str) -> Exercise | None:
        with DbSession(self._engine) as db:
            model = db.get(ExerciseModel, exercise_id)
            if model is None:
                return None
            return _to_entity(model, self._concept_ids(db, exercise_id))
