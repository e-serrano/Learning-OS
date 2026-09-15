from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import Mistake
from app.persistence.models import MistakeModel
from app.persistence.repositories._util import dt_to_str, str_to_dt


def _to_model(mistake: Mistake) -> MistakeModel:
    return MistakeModel(
        id=mistake.id,
        goal_id=mistake.goal_id,
        concept_id=mistake.concept_id,
        type=mistake.type.value,
        description=mistake.description,
        severity=mistake.severity.value,
        occurrences=mistake.occurrences,
        first_seen=dt_to_str(mistake.first_seen),
        last_seen=dt_to_str(mistake.last_seen),
        resolved_at=dt_to_str(mistake.resolved_at),
    )


def _to_entity(model: MistakeModel) -> Mistake:
    return Mistake(
        id=model.id,
        goal_id=model.goal_id,
        concept_id=model.concept_id,
        type=model.type,  # type: ignore[arg-type]
        description=model.description,
        severity=model.severity,  # type: ignore[arg-type]
        occurrences=model.occurrences,
        first_seen=str_to_dt(model.first_seen),  # type: ignore[arg-type]
        last_seen=str_to_dt(model.last_seen),  # type: ignore[arg-type]
        resolved_at=str_to_dt(model.resolved_at),
    )


class SqlMistakeRepository:
    """Implements app.domain.ports.MistakeRepository against mistakes (T033)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, mistake: Mistake) -> None:
        with DbSession(self._engine) as db:
            db.add(_to_model(mistake))
            db.commit()

    def list_by_concept(self, concept_id: str) -> list[Mistake]:
        with DbSession(self._engine) as db:
            stmt = select(MistakeModel).where(MistakeModel.concept_id == concept_id)
            return [_to_entity(m) for m in db.scalars(stmt)]

    def update(self, mistake: Mistake) -> None:
        with DbSession(self._engine) as db:
            db.merge(_to_model(mistake))
            db.commit()
