from datetime import UTC, datetime, timedelta

from app.domain.entities import Concept, ConceptRelation, Evidence, Mistake
from app.domain.enums import (
    ConceptRelationType,
    ConceptStatus,
    EvidenceSourceType,
    MistakeSeverity,
    MistakeType,
)
from app.services.activity_selector import MIN_FACTOR, REVIEW_OVERDUE_CAP, ActivitySelector

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeConceptRepository:
    def __init__(self, concepts: list[Concept]) -> None:
        self._by_id = {c.id: c for c in concepts}

    def get(self, concept_id: str) -> Concept | None:
        return self._by_id.get(concept_id)

    def list_by_goal(self, goal_id: str) -> list[Concept]:
        return list(self._by_id.values())


class FakeConceptRelationRepository:
    def __init__(self, relations: list[ConceptRelation]) -> None:
        self._relations = relations

    def list_prerequisites_of(self, concept_id: str) -> list[ConceptRelation]:
        return [
            r
            for r in self._relations
            if r.target_id == concept_id and r.relation == ConceptRelationType.PREREQUISITE_OF
        ]


class FakeMistakeRepository:
    def __init__(self, mistakes: list[Mistake]) -> None:
        self._mistakes = mistakes

    def list_by_concept(self, concept_id: str) -> list[Mistake]:
        return [m for m in self._mistakes if m.concept_id == concept_id]


class FakeEvidenceRepository:
    def __init__(self, records: list[Evidence]) -> None:
        self._records = records

    def list_by_concept(self, concept_id: str) -> list[Evidence]:
        return [e for e in self._records if e.concept_id == concept_id]


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def _concept(**overrides: object) -> Concept:
    defaults: dict[str, object] = dict(
        id="concept_1",
        title="Window Functions",
        domain="sql",
        status=ConceptStatus.LEARNING,
        mastery=0,
        confidence=0,
        importance=3,
        retention=0,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return Concept(**defaults)  # type: ignore[arg-type]


def _selector(
    concepts: list[Concept],
    relations: list[ConceptRelation] | None = None,
    mistakes: list[Mistake] | None = None,
    evidence: list[Evidence] | None = None,
    now: datetime = NOW,
) -> ActivitySelector:
    return ActivitySelector(
        concepts=FakeConceptRepository(concepts),
        concept_relations=FakeConceptRelationRepository(relations or []),
        mistakes=FakeMistakeRepository(mistakes or []),
        evidence=FakeEvidenceRepository(evidence or []),
        clock=FakeClock(now),
    )


def test_empty_goal_returns_no_candidates() -> None:
    selector = _selector([])

    assert selector.rank("goal_1") == []


def test_breakdown_exposes_all_six_factors() -> None:
    selector = _selector([_concept()])

    [candidate] = selector.rank("goal_1")

    assert set(candidate.breakdown) == {
        "importance",
        "weakness",
        "prerequisite_factor",
        "review_factor",
        "mistake_factor",
        "transfer_factor",
    }


def test_score_is_explainable_as_the_product_of_the_breakdown() -> None:
    selector = _selector([_concept(importance=4, mastery=1)])

    [candidate] = selector.rank("goal_1")

    expected = 1.0
    for factor in candidate.breakdown.values():
        expected *= factor
    assert candidate.score == expected


def test_importance_factor_reflects_concept_importance_directly() -> None:
    selector = _selector([_concept(importance=5)])

    [candidate] = selector.rank("goal_1")

    assert candidate.breakdown["importance"] == 5.0


def test_weakness_is_high_for_low_mastery_and_floored_for_full_mastery() -> None:
    selector = _selector([_concept(id="weak", mastery=0), _concept(id="mastered", mastery=5)])

    by_id = {c.concept_id: c for c in selector.rank("goal_1")}

    assert by_id["weak"].breakdown["weakness"] == 1.0
    assert by_id["mastered"].breakdown["weakness"] == MIN_FACTOR


def test_prerequisite_factor_is_neutral_when_no_prerequisites_exist() -> None:
    selector = _selector([_concept()])

    [candidate] = selector.rank("goal_1")

    assert candidate.breakdown["prerequisite_factor"] == 1.0


def test_prerequisite_factor_reflects_prerequisite_mastery() -> None:
    concepts = [_concept(id="target"), _concept(id="prereq", mastery=2.5)]
    relations = [
        ConceptRelation(
            source_id="prereq", target_id="target", relation=ConceptRelationType.PREREQUISITE_OF
        )
    ]
    selector = _selector(concepts, relations=relations)

    by_id = {c.concept_id: c for c in selector.rank("goal_1")}

    assert by_id["target"].breakdown["prerequisite_factor"] == 0.5


def test_review_factor_is_floored_when_not_yet_due() -> None:
    selector = _selector([_concept(next_review=NOW + timedelta(days=5))])

    [candidate] = selector.rank("goal_1")

    assert candidate.breakdown["review_factor"] == MIN_FACTOR


def test_review_factor_grows_with_days_overdue_and_is_capped() -> None:
    selector = _selector([_concept(next_review=NOW - timedelta(days=1000))])

    [candidate] = selector.rank("goal_1")

    assert candidate.breakdown["review_factor"] == REVIEW_OVERDUE_CAP


def test_mistake_factor_counts_only_unresolved_mistakes() -> None:
    mistakes = [
        Mistake(
            id="m1",
            concept_id="concept_1",
            goal_id="goal_1",
            type=MistakeType.MISCONCEPTION,
            description="open",
            severity=MistakeSeverity.MEDIUM,
            occurrences=1,
            first_seen=NOW,
            last_seen=NOW,
        ),
        Mistake(
            id="m2",
            concept_id="concept_1",
            goal_id="goal_1",
            type=MistakeType.RECALL,
            description="resolved",
            severity=MistakeSeverity.LOW,
            occurrences=1,
            first_seen=NOW,
            last_seen=NOW,
            resolved_at=NOW,
        ),
    ]
    selector = _selector([_concept()], mistakes=mistakes)

    [candidate] = selector.rank("goal_1")

    assert candidate.breakdown["mistake_factor"] == 1.2


def test_transfer_factor_is_neutral_without_evidence() -> None:
    selector = _selector([_concept()])

    [candidate] = selector.rank("goal_1")

    assert candidate.breakdown["transfer_factor"] == 1.0


def test_transfer_factor_is_high_when_transfer_evidence_is_weak() -> None:
    evidence = [
        Evidence(
            id="ev1",
            concept_id="concept_1",
            goal_id="goal_1",
            activity_id="activity_1",
            source_type=EvidenceSourceType.EXERCISE,
            difficulty=3,
            transfer=0.0,
            timestamp=NOW,
        )
    ]
    selector = _selector([_concept()], evidence=evidence)

    [candidate] = selector.rank("goal_1")

    assert candidate.breakdown["transfer_factor"] == 1.0


def test_candidates_are_ranked_highest_score_first() -> None:
    selector = _selector(
        [
            _concept(id="high_priority", importance=5, mastery=0),
            _concept(id="low_priority", importance=1, mastery=5),
        ]
    )

    ranked = selector.rank("goal_1")

    assert [c.concept_id for c in ranked] == ["high_priority", "low_priority"]
