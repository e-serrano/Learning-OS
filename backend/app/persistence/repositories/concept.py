from datetime import datetime

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import Concept
from app.persistence.models import ConceptModel, GoalConceptModel
from app.persistence.repositories._util import dt_to_str, str_to_dt


def _to_model(concept: Concept) -> ConceptModel:
    return ConceptModel(
        id=concept.id,
        title=concept.title,
        domain=concept.domain,
        status=concept.status.value,
        mastery=concept.mastery,
        confidence=concept.confidence,
        importance=concept.importance,
        retention=concept.retention,
        last_practiced=dt_to_str(concept.last_practiced),
        next_review=dt_to_str(concept.next_review),
        obsidian_path=concept.obsidian_path,
        created_at=dt_to_str(concept.created_at),
        updated_at=dt_to_str(concept.updated_at),
    )


def _to_entity(model: ConceptModel) -> Concept:
    return Concept(
        id=model.id,
        title=model.title,
        domain=model.domain,
        status=model.status,  # type: ignore[arg-type]
        mastery=model.mastery,
        confidence=model.confidence,
        importance=model.importance,
        retention=model.retention,
        last_practiced=str_to_dt(model.last_practiced),
        next_review=str_to_dt(model.next_review),
        obsidian_path=model.obsidian_path,
        created_at=str_to_dt(model.created_at),  # type: ignore[arg-type]
        updated_at=str_to_dt(model.updated_at),  # type: ignore[arg-type]
    )


class SqlConceptRepository:
    """Implements app.domain.ports.ConceptRepository against concepts (T033)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, concept: Concept) -> None:
        with DbSession(self._engine) as db:
            db.add(_to_model(concept))
            db.commit()

    def get(self, concept_id: str) -> Concept | None:
        with DbSession(self._engine) as db:
            model = db.get(ConceptModel, concept_id)
            return _to_entity(model) if model is not None else None

    def list_by_goal(self, goal_id: str) -> list[Concept]:
        with DbSession(self._engine) as db:
            stmt = (
                select(ConceptModel)
                .join(GoalConceptModel, GoalConceptModel.concept_id == ConceptModel.id)
                .where(GoalConceptModel.goal_id == goal_id)
            )
            return [_to_entity(m) for m in db.scalars(stmt)]

    def list_due_for_review(self, before: datetime) -> list[Concept]:
        with DbSession(self._engine) as db:
            stmt = select(ConceptModel).where(
                ConceptModel.next_review.is_not(None),
                ConceptModel.next_review <= dt_to_str(before),
            )
            return [_to_entity(m) for m in db.scalars(stmt)]

    def update(self, concept: Concept) -> None:
        with DbSession(self._engine) as db:
            db.merge(_to_model(concept))
            db.commit()

    def link_to_goal(self, goal_id: str, concept_id: str, importance: int = 3) -> None:
        """Populate goal_concepts -- required for list_by_goal to find anything."""
        with DbSession(self._engine) as db:
            existing = db.get(GoalConceptModel, (goal_id, concept_id))
            if existing is None:
                db.add(
                    GoalConceptModel(goal_id=goal_id, concept_id=concept_id, importance=importance)
                )
                db.commit()
