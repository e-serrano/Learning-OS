from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import ConceptRelation
from app.domain.enums import ConceptRelationType
from app.persistence.models import ConceptRelationModel


def _to_model(relation: ConceptRelation) -> ConceptRelationModel:
    return ConceptRelationModel(
        source_id=relation.source_id,
        target_id=relation.target_id,
        relation=relation.relation.value,
        weight=relation.weight,
    )


def _to_entity(model: ConceptRelationModel) -> ConceptRelation:
    return ConceptRelation(
        source_id=model.source_id,
        target_id=model.target_id,
        relation=model.relation,  # type: ignore[arg-type]
        weight=model.weight,
    )


class SqlConceptRelationRepository:
    """Implements app.domain.ports.ConceptRelationRepository against
    concept_relations (docs/DATABASE_SCHEMA.md #2)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, relation: ConceptRelation) -> None:
        with DbSession(self._engine) as db:
            db.add(_to_model(relation))
            db.commit()

    def list_prerequisites_of(self, concept_id: str) -> list[ConceptRelation]:
        """A relation `source PREREQUISITE_OF target` means source must be
        learned before target -- so target's prerequisites are the sources
        of relations pointing at it."""
        with DbSession(self._engine) as db:
            stmt = select(ConceptRelationModel).where(
                ConceptRelationModel.target_id == concept_id,
                ConceptRelationModel.relation == ConceptRelationType.PREREQUISITE_OF.value,
            )
            return [_to_entity(m) for m in db.scalars(stmt)]
