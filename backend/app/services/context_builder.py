"""Context builder -- selects only relevant material for an `AIRequest`,
never the full vault by default (docs/TASKS.md T060, docs/AI_CONTRACTS.md
#12).

Ranking signals implemented: goal relevance, concept relevance,
prerequisite relationship, recent mistakes, recent practice. Semantic
similarity (also listed in AI_CONTRACTS.md #12) has embeddings
infrastructure now (docs/TASKS.md T128/T129, `SemanticSearchService`)
but is deliberately not wired in here -- doing so would make every
caller of this class newly require the user's default AI provider to
support embeddings, which Anthropic does not, silently breaking a
working deployment. See docs/AI_CONTRACTS.md #12's own note.
"""

from typing import Any

from app.domain.entities import Concept, ConceptRelation, Evidence, LearningGoal, Mistake
from app.domain.ports import (
    ConceptRelationRepository,
    ConceptRepository,
    EvidenceRepository,
    GoalRepository,
    MistakeRepository,
)

DEFAULT_MAX_PREREQUISITES = 5
DEFAULT_MAX_MISTAKES = 5
DEFAULT_MAX_RECENT_EVIDENCE = 5


class GoalNotFoundError(Exception):
    pass


class ConceptNotFoundError(Exception):
    pass


def _goal_item(goal: LearningGoal) -> dict[str, Any]:
    return {
        "kind": "goal",
        "id": goal.id,
        "title": goal.title,
        "target_level": goal.target_level.value,
    }


def _concept_item(concept: Concept) -> dict[str, Any]:
    return {
        "kind": "concept",
        "id": concept.id,
        "title": concept.title,
        "status": concept.status.value,
        "mastery": concept.mastery,
        "confidence": concept.confidence,
        "importance": concept.importance,
        "retention": concept.retention,
    }


def _prerequisite_item(concept: Concept) -> dict[str, Any]:
    return {
        "kind": "prerequisite",
        "id": concept.id,
        "title": concept.title,
        "status": concept.status.value,
        "mastery": concept.mastery,
    }


def _mistake_item(mistake: Mistake) -> dict[str, Any]:
    return {
        "kind": "mistake",
        "id": mistake.id,
        "type": mistake.type.value,
        "description": mistake.description,
        "severity": mistake.severity.value,
        "occurrences": mistake.occurrences,
    }


def _practice_item(evidence: Evidence) -> dict[str, Any]:
    return {
        "kind": "practice",
        "id": evidence.id,
        "source_type": evidence.source_type.value,
        "difficulty": evidence.difficulty,
        "correctness": evidence.correctness,
        "timestamp": evidence.timestamp.isoformat(),
    }


class ContextBuilder:
    def __init__(
        self,
        goals: GoalRepository,
        concepts: ConceptRepository,
        concept_relations: ConceptRelationRepository,
        evidence: EvidenceRepository,
        mistakes: MistakeRepository,
        max_prerequisites: int = DEFAULT_MAX_PREREQUISITES,
        max_mistakes: int = DEFAULT_MAX_MISTAKES,
        max_recent_evidence: int = DEFAULT_MAX_RECENT_EVIDENCE,
    ) -> None:
        self._goals = goals
        self._concepts = concepts
        self._concept_relations = concept_relations
        self._evidence = evidence
        self._mistakes = mistakes
        self._max_prerequisites = max_prerequisites
        self._max_mistakes = max_mistakes
        self._max_recent_evidence = max_recent_evidence

    def build(self, goal_id: str, concept_id: str) -> list[dict[str, Any]]:
        goal = self._goals.get(goal_id)
        if goal is None:
            raise GoalNotFoundError(goal_id)
        concept = self._concepts.get(concept_id)
        if concept is None:
            raise ConceptNotFoundError(concept_id)

        context: list[dict[str, Any]] = [_goal_item(goal), _concept_item(concept)]
        context.extend(self._prerequisite_items(concept_id))
        context.extend(self._mistake_items(concept_id))
        context.extend(self._practice_items(concept_id))
        return context

    def _prerequisite_items(self, concept_id: str) -> list[dict[str, Any]]:
        relations: list[ConceptRelation] = self._concept_relations.list_prerequisites_of(concept_id)
        items: list[dict[str, Any]] = []
        for relation in relations[: self._max_prerequisites]:
            prerequisite = self._concepts.get(relation.source_id)
            if prerequisite is not None:
                items.append(_prerequisite_item(prerequisite))
        return items

    def _mistake_items(self, concept_id: str) -> list[dict[str, Any]]:
        unresolved = [
            m for m in self._mistakes.list_by_concept(concept_id) if m.resolved_at is None
        ]
        unresolved.sort(key=lambda m: m.last_seen, reverse=True)
        return [_mistake_item(m) for m in unresolved[: self._max_mistakes]]

    def _practice_items(self, concept_id: str) -> list[dict[str, Any]]:
        recent = sorted(
            self._evidence.list_by_concept(concept_id),
            key=lambda e: e.timestamp,
            reverse=True,
        )
        return [_practice_item(e) for e in recent[: self._max_recent_evidence]]
