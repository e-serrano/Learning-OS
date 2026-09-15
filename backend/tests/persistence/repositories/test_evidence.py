from datetime import UTC, datetime

from sqlalchemy import Engine

from app.domain.entities import Evidence
from app.domain.enums import EvidenceSourceType
from app.domain.ports import EvidenceRepository
from app.persistence.repositories import SqlEvidenceRepository

NOW = datetime.now(UTC)


def _accepts_port(port: EvidenceRepository) -> EvidenceRepository:
    return port


def _make_evidence(seeded: dict, **overrides: object) -> Evidence:  # type: ignore[type-arg]
    defaults: dict[str, object] = dict(
        id="evidence_1",
        concept_id=seeded["concept_id"],
        goal_id=seeded["goal_id"],
        session_id=seeded["session_id"],
        activity_id=seeded["activity_id"],
        source_type=EvidenceSourceType.EXERCISE,
        difficulty=2,
        correctness=0.8,
        timestamp=NOW,
    )
    defaults.update(overrides)
    return Evidence(**defaults)  # type: ignore[arg-type]


def test_satisfies_evidence_repository_port(engine: Engine) -> None:
    _accepts_port(SqlEvidenceRepository(engine))


def test_evidence_repository_has_no_update_or_delete_method() -> None:
    """Append-only -- see docs/AGENTS.md #8."""
    assert not hasattr(SqlEvidenceRepository, "update")
    assert not hasattr(SqlEvidenceRepository, "delete")


def test_add_then_list_by_concept_roundtrips(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlEvidenceRepository(engine)
    evidence = _make_evidence(seeded)
    repo.add(evidence)

    results = repo.list_by_concept(seeded["concept_id"])
    assert results == [evidence]


def test_list_by_goal_returns_matching_records(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlEvidenceRepository(engine)
    repo.add(_make_evidence(seeded, id="evidence_1"))
    repo.add(_make_evidence(seeded, id="evidence_2"))

    results = repo.list_by_goal(seeded["goal_id"])
    assert {e.id for e in results} == {"evidence_1", "evidence_2"}


def test_evidence_accumulates_rather_than_overwrites(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlEvidenceRepository(engine)
    repo.add(_make_evidence(seeded, id="evidence_1", correctness=0.5))
    repo.add(_make_evidence(seeded, id="evidence_1_b", correctness=0.9))

    results = repo.list_by_concept(seeded["concept_id"])
    assert len(results) == 2


def test_metadata_and_skill_ids_roundtrip(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlEvidenceRepository(engine)
    evidence = _make_evidence(
        seeded, metadata={"note": "good attempt"}, skill_ids=["skill_1", "skill_2"]
    )
    repo.add(evidence)

    loaded = repo.list_by_concept(seeded["concept_id"])[0]
    assert loaded.metadata == {"note": "good attempt"}
    assert loaded.skill_ids == ["skill_1", "skill_2"]
