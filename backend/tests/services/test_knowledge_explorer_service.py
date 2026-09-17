from datetime import UTC, datetime

import pytest

from app.domain.entities import Concept, ConceptRelation, LearningGoal
from app.domain.enums import ConceptRelationType, ConceptStatus, TargetLevel
from app.services.knowledge_explorer_service import (
    ConceptNotFoundError,
    GoalNotFoundError,
    KnowledgeExplorerService,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeGoalRepository:
    def __init__(self, goals: list[LearningGoal]) -> None:
        self._by_id = {g.id: g for g in goals}

    def get(self, goal_id: str) -> LearningGoal | None:
        return self._by_id.get(goal_id)

    def add(self, goal: LearningGoal) -> None:
        self._by_id[goal.id] = goal

    def list_all(self) -> list[LearningGoal]:
        return list(self._by_id.values())

    def update(self, goal: LearningGoal) -> None:
        self._by_id[goal.id] = goal


class FakeConceptRepository:
    def __init__(self, concepts: list[Concept]) -> None:
        self._by_id = {c.id: c for c in concepts}

    def add(self, concept: Concept) -> None:
        self._by_id[concept.id] = concept

    def get(self, concept_id: str) -> Concept | None:
        return self._by_id.get(concept_id)

    def list_by_goal(self, goal_id: str) -> list[Concept]:
        return list(self._by_id.values())

    def list_due_for_review(self, before: datetime) -> list[Concept]:
        return [c for c in self._by_id.values() if c.next_review and c.next_review < before]

    def update(self, concept: Concept) -> None:
        self._by_id[concept.id] = concept

    def link_to_goal(self, goal_id: str, concept_id: str, importance: int = 3) -> None:
        raise NotImplementedError


class FakeConceptRelationRepository:
    def __init__(self, relations: list[ConceptRelation]) -> None:
        self._relations = relations

    def add(self, relation: ConceptRelation) -> None:
        self._relations.append(relation)

    def list_prerequisites_of(self, concept_id: str) -> list[ConceptRelation]:
        return [r for r in self._relations if r.target_id == concept_id]

    def list_relations_from(self, concept_id: str) -> list[ConceptRelation]:
        return [r for r in self._relations if r.source_id == concept_id]


def _goal(**overrides: object) -> LearningGoal:
    defaults: dict[str, object] = dict(
        id="goal_1",
        title="Learn BigQuery",
        target_level=TargetLevel.PROFESSIONAL,
        status="active",
        priority=3,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return LearningGoal(**defaults)  # type: ignore[arg-type]


def _concept(**overrides: object) -> Concept:
    defaults: dict[str, object] = dict(
        id="concept_1",
        title="Window functions",
        domain="sql",
        status=ConceptStatus.LEARNING,
        mastery=1.0,
        confidence=50.0,
        importance=3,
        retention=50.0,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return Concept(**defaults)  # type: ignore[arg-type]


def _service(
    goals: list[LearningGoal] | None = None,
    concepts: list[Concept] | None = None,
    relations: list[ConceptRelation] | None = None,
) -> KnowledgeExplorerService:
    return KnowledgeExplorerService(
        FakeGoalRepository(goals if goals is not None else [_goal()]),
        FakeConceptRepository(concepts if concepts is not None else [_concept()]),
        FakeConceptRelationRepository(relations if relations is not None else []),
    )


def test_list_concepts_returns_all_for_goal() -> None:
    service = _service(concepts=[_concept(id="c1"), _concept(id="c2")])

    concepts = service.list_concepts("goal_1")

    assert {c.id for c in concepts} == {"c1", "c2"}


def test_list_concepts_raises_when_goal_missing() -> None:
    service = _service(goals=[])

    with pytest.raises(GoalNotFoundError):
        service.list_concepts("missing")


def test_list_concepts_filters_by_status() -> None:
    service = _service(
        concepts=[
            _concept(id="c1", status=ConceptStatus.MASTERED),
            _concept(id="c2", status=ConceptStatus.LEARNING),
        ]
    )

    concepts = service.list_concepts("goal_1", status=ConceptStatus.MASTERED)

    assert [c.id for c in concepts] == ["c1"]


def test_list_concepts_filters_by_mastery_lt() -> None:
    service = _service(
        concepts=[
            _concept(id="c1", mastery=1.0),
            _concept(id="c2", mastery=4.0),
        ]
    )

    concepts = service.list_concepts("goal_1", mastery_lt=2.0)

    assert [c.id for c in concepts] == ["c1"]


def test_list_concepts_filters_by_next_review_before() -> None:
    service = _service(
        concepts=[
            _concept(id="c1", next_review=datetime(2026, 1, 5, tzinfo=UTC)),
            _concept(id="c2", next_review=datetime(2026, 2, 1, tzinfo=UTC)),
            _concept(id="c3", next_review=None),
        ]
    )

    concepts = service.list_concepts("goal_1", next_review_before=datetime(2026, 1, 10, tzinfo=UTC))

    assert [c.id for c in concepts] == ["c1"]


def test_get_concept_returns_it() -> None:
    service = _service(concepts=[_concept(id="c1")])

    assert service.get_concept("c1").id == "c1"


def test_get_concept_raises_when_missing() -> None:
    service = _service(concepts=[])

    with pytest.raises(ConceptNotFoundError):
        service.get_concept("missing")


def test_list_relations_returns_outgoing_relations() -> None:
    service = _service(
        concepts=[_concept(id="c1")],
        relations=[
            ConceptRelation(
                source_id="c1", target_id="c2", relation=ConceptRelationType.RELATED_TO
            ),
            ConceptRelation(
                source_id="c2", target_id="c1", relation=ConceptRelationType.PREREQUISITE_OF
            ),
        ],
    )

    relations = service.list_relations("c1")

    assert len(relations) == 1
    assert relations[0].target_id == "c2"


def test_list_relations_raises_when_concept_missing() -> None:
    service = _service(concepts=[])

    with pytest.raises(ConceptNotFoundError):
        service.list_relations("missing")
