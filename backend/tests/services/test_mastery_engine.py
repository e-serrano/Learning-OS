from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entities import Concept, Evidence
from app.domain.enums import ConceptStatus, EvidenceSourceType
from app.services.mastery_engine import MasteryEngine, MasteryWeights

NOW = datetime.now(UTC)


class FakeEvidenceRepository:
    def __init__(self, records: list[Evidence]) -> None:
        self._records = records

    def add(self, evidence: Evidence) -> None:
        self._records.append(evidence)

    def list_by_concept(self, concept_id: str) -> list[Evidence]:
        return [e for e in self._records if e.concept_id == concept_id]

    def list_by_goal(self, goal_id: str) -> list[Evidence]:
        return [e for e in self._records if e.goal_id == goal_id]


def _concept(**overrides: object) -> Concept:
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


def _evidence(index: int, **overrides: object) -> Evidence:
    defaults: dict[str, object] = dict(
        id=f"evidence_{index}",
        concept_id="concept_1",
        goal_id="goal_1",
        activity_id="activity_1",
        source_type=EvidenceSourceType.EXERCISE,
        difficulty=3,
        correctness=1.0,
        transfer=1.0,
        independence=1.0,
        timestamp=NOW + timedelta(hours=index),
    )
    defaults.update(overrides)
    return Evidence(**defaults)  # type: ignore[arg-type]


def test_no_evidence_yields_unknown_status_and_zero_mastery() -> None:
    engine = MasteryEngine(FakeEvidenceRepository([]))

    result = engine.compute(_concept())

    assert result.mastery == 0.0
    assert result.status == ConceptStatus.UNKNOWN


def test_perfect_evidence_and_full_retention_yields_max_mastery() -> None:
    evidence = FakeEvidenceRepository([_evidence(0)])
    engine = MasteryEngine(evidence)

    result = engine.compute(_concept(retention=100))

    assert result.mastery == 5.0
    assert result.status == ConceptStatus.MASTERED


def test_recent_window_excludes_older_records_from_recent_performance() -> None:
    records = [_evidence(0, correctness=0.0)] + [_evidence(i, correctness=1.0) for i in range(1, 6)]
    engine = MasteryEngine(FakeEvidenceRepository(records), recent_window=5)

    result = engine.compute(_concept(retention=100))

    # recent_performance = 1.0 (last 5), historical_performance = 5/6 (all 6)
    expected = (0.35 * 1.0 + 0.20 * (5 / 6) + 0.20 * 1.0 + 0.15 * 1.0 + 0.10 * 1.0) * 5
    assert result.mastery == pytest.approx(round(expected, 2))


def test_weak_recent_performance_forces_weak_status_regardless_of_mastery_tier() -> None:
    records = [_evidence(i, correctness=0.2) for i in range(5)]
    engine = MasteryEngine(FakeEvidenceRepository(records))

    result = engine.compute(_concept(retention=100))

    assert result.status == ConceptStatus.WEAK
    assert result.mastery > 2.0  # tier would otherwise be USABLE or higher


def test_none_evidence_fields_are_excluded_from_the_average_not_treated_as_zero() -> None:
    records = [
        _evidence(0, correctness=None, source_type=EvidenceSourceType.SELF_REPORT),
        _evidence(1, correctness=1.0),
    ]
    engine = MasteryEngine(FakeEvidenceRepository(records))

    result = engine.compute(_concept(retention=100))

    assert result.mastery == 5.0  # average of [1.0], not average of [0.0, 1.0]


def test_all_none_field_falls_back_to_zero_without_erroring() -> None:
    records = [_evidence(0, transfer=None)]
    engine = MasteryEngine(FakeEvidenceRepository(records))

    result = engine.compute(_concept(retention=100))

    expected = (0.35 * 1.0 + 0.20 * 1.0 + 0.20 * 0.0 + 0.15 * 1.0 + 0.10 * 1.0) * 5
    assert result.mastery == pytest.approx(round(expected, 2))


def test_weights_are_configurable_and_actually_used() -> None:
    records = [_evidence(0, correctness=0.6, transfer=0.0, independence=0.0)]
    engine = MasteryEngine(
        FakeEvidenceRepository(records),
        weights=MasteryWeights(
            recent_performance=1.0,
            historical_performance=0.0,
            transfer_performance=0.0,
            independence=0.0,
            retention=0.0,
        ),
    )

    result = engine.compute(_concept(retention=0))

    assert result.mastery == 3.0  # 0.6 * 5, ignoring transfer/independence/retention entirely


def test_mastery_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="must sum to 1.0"):
        MasteryWeights(recent_performance=0.9)


def test_compute_never_mutates_the_input_concept() -> None:
    concept = _concept(mastery=0, status=ConceptStatus.UNKNOWN, retention=100)
    engine = MasteryEngine(FakeEvidenceRepository([_evidence(0)]))

    engine.compute(concept)

    assert concept.mastery == 0
    assert concept.status == ConceptStatus.UNKNOWN
