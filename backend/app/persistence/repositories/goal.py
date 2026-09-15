from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import LearningGoal
from app.persistence.models import GoalModel
from app.persistence.repositories._util import dt_to_str, str_to_dt


def _to_model(goal: LearningGoal) -> GoalModel:
    return GoalModel(
        id=goal.id,
        title=goal.title,
        description=goal.description,
        domain=goal.domain,
        target_level=goal.target_level.value,
        status=goal.status.value,
        priority=goal.priority,
        deadline=dt_to_str(goal.deadline),
        available_minutes_per_week=goal.available_minutes_per_week,
        created_at=dt_to_str(goal.created_at),
        updated_at=dt_to_str(goal.updated_at),
    )


def _to_entity(model: GoalModel) -> LearningGoal:
    return LearningGoal(
        id=model.id,
        title=model.title,
        description=model.description,
        domain=model.domain,
        target_level=model.target_level,  # type: ignore[arg-type]
        status=model.status,  # type: ignore[arg-type]
        priority=model.priority,
        deadline=str_to_dt(model.deadline),
        available_minutes_per_week=model.available_minutes_per_week,
        created_at=str_to_dt(model.created_at),  # type: ignore[arg-type]
        updated_at=str_to_dt(model.updated_at),  # type: ignore[arg-type]
    )


class SqlGoalRepository:
    """Implements app.domain.ports.GoalRepository against goals (T033)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, goal: LearningGoal) -> None:
        with DbSession(self._engine) as db:
            db.add(_to_model(goal))
            db.commit()

    def get(self, goal_id: str) -> LearningGoal | None:
        with DbSession(self._engine) as db:
            model = db.get(GoalModel, goal_id)
            return _to_entity(model) if model is not None else None

    def list_all(self) -> list[LearningGoal]:
        with DbSession(self._engine) as db:
            return [_to_entity(m) for m in db.scalars(select(GoalModel))]

    def update(self, goal: LearningGoal) -> None:
        with DbSession(self._engine) as db:
            db.merge(_to_model(goal))
            db.commit()
