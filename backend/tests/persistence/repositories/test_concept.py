from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine

from app.domain.entities import Concept
from app.domain.enums import ConceptStatus
from app.domain.ports import ConceptRepository
from app.persistence.repositories import SqlConceptRepository

NOW = datetime.now(UTC)


def _accepts_port(port: ConceptRepository) -> ConceptRepository:
    return port


def _make_concept(**overrides: object) -> Concept:
    defaults: dict[str, object] = dict(
        id="concept_1",
        title="Window Functions",
        domain="sql",
        status=ConceptStatus.UNKNOWN,
        mastery=0,
        confidence=0,
        importance=3,
        retention=0,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return Concept(**defaults)  # type: ignore[arg-type]


def test_satisfies_concept_repository_port(engine: Engine) -> None:
    _accepts_port(SqlConceptRepository(engine))


def test_add_then_get_roundtrips(engine: Engine) -> None:
    repo = SqlConceptRepository(engine)
    concept = _make_concept()
    repo.add(concept)

    assert repo.get("concept_1") == concept


def test_update_persists_changes(engine: Engine) -> None:
    repo = SqlConceptRepository(engine)
    repo.add(_make_concept())
    repo.update(_make_concept(mastery=3.5, status=ConceptStatus.USABLE))

    loaded = repo.get("concept_1")
    assert loaded is not None
    assert loaded.mastery == 3.5
    assert loaded.status == ConceptStatus.USABLE


def test_list_by_goal_returns_only_linked_concepts(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlConceptRepository(engine)
    repo.add(_make_concept(id="concept_linked"))
    repo.add(_make_concept(id="concept_unlinked"))
    repo.link_to_goal(seeded["goal_id"], "concept_linked")

    linked = {c.id for c in repo.list_by_goal(seeded["goal_id"])}
    assert linked == {"concept_linked"}


def test_list_due_for_review_filters_by_next_review(engine: Engine) -> None:
    repo = SqlConceptRepository(engine)
    repo.add(_make_concept(id="due", next_review=NOW - timedelta(days=1)))
    repo.add(_make_concept(id="not_due", next_review=NOW + timedelta(days=10)))
    repo.add(_make_concept(id="never_reviewed"))

    due = {c.id for c in repo.list_due_for_review(NOW)}
    assert due == {"due"}
