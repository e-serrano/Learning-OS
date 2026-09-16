from datetime import UTC, datetime

from sqlalchemy import Engine

from app.domain.entities import Concept, ConceptRelation
from app.domain.enums import ConceptRelationType, ConceptStatus
from app.domain.ports import ConceptRelationRepository
from app.persistence.repositories import SqlConceptRelationRepository, SqlConceptRepository

NOW = datetime.now(UTC)


def _accepts_port(port: ConceptRelationRepository) -> ConceptRelationRepository:
    return port


def _make_concept(concept_id: str) -> Concept:
    return Concept(
        id=concept_id,
        title=concept_id,
        domain="sql",
        status=ConceptStatus.UNKNOWN,
        mastery=0,
        confidence=0,
        importance=3,
        retention=0,
        created_at=NOW,
        updated_at=NOW,
    )


def test_satisfies_concept_relation_repository_port(engine: Engine) -> None:
    _accepts_port(SqlConceptRelationRepository(engine))


def test_add_then_list_prerequisites_of_roundtrips(engine: Engine) -> None:
    concepts = SqlConceptRepository(engine)
    concepts.add(_make_concept("select"))
    concepts.add(_make_concept("window_functions"))
    relations = SqlConceptRelationRepository(engine)
    relations.add(
        ConceptRelation(
            source_id="select",
            target_id="window_functions",
            relation=ConceptRelationType.PREREQUISITE_OF,
        )
    )

    found = relations.list_prerequisites_of("window_functions")

    assert found == [
        ConceptRelation(
            source_id="select",
            target_id="window_functions",
            relation=ConceptRelationType.PREREQUISITE_OF,
        )
    ]


def test_list_prerequisites_of_excludes_other_relation_types(engine: Engine) -> None:
    concepts = SqlConceptRepository(engine)
    concepts.add(_make_concept("cte"))
    concepts.add(_make_concept("window_functions"))
    relations = SqlConceptRelationRepository(engine)
    relations.add(
        ConceptRelation(
            source_id="cte", target_id="window_functions", relation=ConceptRelationType.RELATED_TO
        )
    )

    assert relations.list_prerequisites_of("window_functions") == []


def test_list_prerequisites_of_excludes_other_targets(engine: Engine) -> None:
    concepts = SqlConceptRepository(engine)
    concepts.add(_make_concept("select"))
    concepts.add(_make_concept("window_functions"))
    concepts.add(_make_concept("subqueries"))
    relations = SqlConceptRelationRepository(engine)
    relations.add(
        ConceptRelation(
            source_id="select",
            target_id="window_functions",
            relation=ConceptRelationType.PREREQUISITE_OF,
        )
    )

    assert relations.list_prerequisites_of("subqueries") == []
