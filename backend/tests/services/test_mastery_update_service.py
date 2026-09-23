from datetime import UTC, datetime

import pytest

from app.domain.entities import Concept, Evidence
from app.domain.enums import ConceptStatus, EvidenceSourceType
from app.services.context_builder import ConceptNotFoundError
from app.services.mastery_engine import MasteryEngine
from app.services.mastery_update_service import MasteryUpdateService

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
        status=ConceptStatus.UNKNOWN,
        mastery=0,
        confidence=0,
        importance=3,
        retention=100,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return Concept(**defaults)  # type: ignore[arg-type]


def _evidence(**overrides: object) -> Evidence:
    defaults: dict[str, object] = dict(
        id="evidence_1",
        concept_id="concept_1",
        goal_id="goal_1",
        activity_id="activity_1",
        source_type=EvidenceSourceType.EXERCISE,
        difficulty=3,
        correctness=1.0,
        transfer=1.0,
        independence=1.0,
        timestamp=NOW,
    )
    defaults.update(overrides)
    return Evidence(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_update_mastery_persists_the_recomputed_concept() -> None:
    concepts = FakeConceptRepository([_concept()])
    engine = MasteryEngine(FakeEvidenceRepository([_evidence()]))
    service = MasteryUpdateService(concepts, engine)

    updated = await service.update_mastery("concept_1", "goal_1")

    assert updated.mastery == 5.0
    assert updated.status == ConceptStatus.MASTERED
    assert concepts.get("concept_1") == updated


@pytest.mark.asyncio
async def test_update_mastery_raises_when_concept_not_found() -> None:
    concepts = FakeConceptRepository([])
    engine = MasteryEngine(FakeEvidenceRepository([]))
    service = MasteryUpdateService(concepts, engine)

    with pytest.raises(ConceptNotFoundError):
        await service.update_mastery("missing_concept", "goal_1")


@pytest.mark.asyncio
async def test_update_mastery_reflects_new_evidence_added_since_last_recalculation() -> None:
    concepts = FakeConceptRepository([_concept(mastery=0, status=ConceptStatus.UNKNOWN)])
    engine = MasteryEngine(FakeEvidenceRepository([_evidence(correctness=0.2)]))
    service = MasteryUpdateService(concepts, engine)

    first = await service.update_mastery("concept_1", "goal_1")
    assert first.status == ConceptStatus.WEAK

    engine_with_more_evidence = MasteryEngine(
        FakeEvidenceRepository([_evidence(correctness=0.2), _evidence(id="evidence_2")])
    )
    service_second = MasteryUpdateService(concepts, engine_with_more_evidence)
    second = await service_second.update_mastery("concept_1", "goal_1")

    assert second.mastery > first.mastery


class FakeCurationTrigger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ConceptStatus, Concept]] = []

    async def trigger_if_newly_mastered(
        self, goal_id: str, previous_status: ConceptStatus, updated: Concept
    ) -> None:
        self.calls.append((goal_id, previous_status, updated))
        return None


@pytest.mark.asyncio
async def test_update_mastery_fires_the_curation_trigger_on_transition_into_mastered() -> None:
    concepts = FakeConceptRepository([_concept(status=ConceptStatus.STRONG)])
    engine = MasteryEngine(FakeEvidenceRepository([_evidence()]))
    trigger = FakeCurationTrigger()
    service = MasteryUpdateService(concepts, engine, trigger)

    updated = await service.update_mastery("concept_1", "goal_1")

    assert updated.status == ConceptStatus.MASTERED
    assert trigger.calls == [("goal_1", ConceptStatus.STRONG, updated)]


@pytest.mark.asyncio
async def test_update_mastery_always_reports_old_and_new_status_to_the_trigger() -> None:
    """`MasteryUpdateService` unconditionally hands both statuses to the
    trigger on every call -- deciding whether that's an actual transition
    into MASTERED is `MasteryCurationTriggerService`'s own job (see
    test_mastery_curation_trigger_service.py), not duplicated here."""
    concepts = FakeConceptRepository([_concept(status=ConceptStatus.UNKNOWN, mastery=0)])
    engine = MasteryEngine(FakeEvidenceRepository([_evidence(correctness=0.2)]))
    trigger = FakeCurationTrigger()
    service = MasteryUpdateService(concepts, engine, trigger)

    updated = await service.update_mastery("concept_1", "goal_1")

    assert updated.status != ConceptStatus.MASTERED
    assert trigger.calls == [("goal_1", ConceptStatus.UNKNOWN, updated)]


@pytest.mark.asyncio
async def test_update_mastery_works_with_no_curation_trigger_configured() -> None:
    concepts = FakeConceptRepository([_concept()])
    engine = MasteryEngine(FakeEvidenceRepository([_evidence()]))
    service = MasteryUpdateService(concepts, engine)

    updated = await service.update_mastery("concept_1", "goal_1")

    assert updated.status == ConceptStatus.MASTERED
