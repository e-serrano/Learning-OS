from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entities import Concept, Evidence
from app.domain.enums import ConceptStatus, EvidenceSourceType
from app.services.context_builder import ConceptNotFoundError
from app.services.retention_update_service import RetentionUpdateService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeConceptRepository:
    def __init__(self, concepts: list[Concept]) -> None:
        self._by_id = {c.id: c for c in concepts}

    def get(self, concept_id: str) -> Concept | None:
        return self._by_id.get(concept_id)

    def update(self, concept: Concept) -> None:
        self._by_id[concept.id] = concept


class FakeEvidenceRepository:
    def __init__(self, records: list[Evidence]) -> None:
        self._records = records

    def list_by_concept(self, concept_id: str) -> list[Evidence]:
        return [e for e in self._records if e.concept_id == concept_id]


def _concept(**overrides: object) -> Concept:
    defaults: dict[str, object] = dict(
        id="concept_1",
        title="Window Functions",
        domain="sql",
        status=ConceptStatus.USABLE,
        mastery=3,
        confidence=50,
        importance=3,
        retention=20,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return Concept(**defaults)  # type: ignore[arg-type]


def _evidence(index: int, **overrides: object) -> Evidence:
    defaults: dict[str, object] = dict(
        id=f"evidence_{index}",
        concept_id="concept_1",
        goal_id="goal_1",
        activity_id="activity_1",
        source_type=EvidenceSourceType.REVIEW,
        difficulty=3,
        correctness=1.0,
        timestamp=NOW + timedelta(hours=index),
    )
    defaults.update(overrides)
    return Evidence(**defaults)  # type: ignore[arg-type]


def test_update_retention_averages_review_evidence_correctness() -> None:
    concepts = FakeConceptRepository([_concept()])
    evidence = FakeEvidenceRepository(
        [_evidence(0, correctness=0.6), _evidence(1, correctness=1.0)]
    )
    service = RetentionUpdateService(concepts, evidence)

    updated = service.update_retention("concept_1")

    assert updated.retention == 80.0
    assert concepts.get("concept_1").retention == 80.0  # type: ignore[union-attr]


def test_update_retention_ignores_non_review_evidence() -> None:
    concepts = FakeConceptRepository([_concept()])
    evidence = FakeEvidenceRepository(
        [
            _evidence(0, correctness=1.0, source_type=EvidenceSourceType.REVIEW),
            _evidence(1, correctness=0.0, source_type=EvidenceSourceType.EXERCISE),
        ]
    )
    service = RetentionUpdateService(concepts, evidence)

    updated = service.update_retention("concept_1")

    assert updated.retention == 100.0  # only the review evidence counts


def test_update_retention_leaves_concept_unchanged_when_no_review_evidence() -> None:
    concepts = FakeConceptRepository([_concept(retention=42)])
    evidence = FakeEvidenceRepository(
        [_evidence(0, source_type=EvidenceSourceType.EXERCISE, correctness=0.1)]
    )
    service = RetentionUpdateService(concepts, evidence)

    updated = service.update_retention("concept_1")

    assert updated.retention == 42
    assert concepts.get("concept_1").retention == 42  # type: ignore[union-attr]


def test_update_retention_uses_only_the_recent_window() -> None:
    concepts = FakeConceptRepository([_concept()])
    old_and_bad = [_evidence(i, correctness=0.0) for i in range(3)]
    recent_and_good = [_evidence(i, correctness=1.0) for i in range(3, 8)]
    evidence = FakeEvidenceRepository(old_and_bad + recent_and_good)
    service = RetentionUpdateService(concepts, evidence, recent_window=5)

    updated = service.update_retention("concept_1")

    assert updated.retention == 100.0  # only the 5 most recent (all correctness=1.0)


def test_update_retention_raises_when_concept_not_found() -> None:
    service = RetentionUpdateService(FakeConceptRepository([]), FakeEvidenceRepository([]))

    with pytest.raises(ConceptNotFoundError):
        service.update_retention("missing_concept")
