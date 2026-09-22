"""Activity selector -- ranks candidate concepts for the next activity
(docs/TASKS.md T064, docs/DOMAIN_MODEL.md #19: "Each candidate activity
receives: priority = importance * weakness * prerequisite_factor *
review_factor * mistake_factor * transfer_factor. The implementation may
refine the formula, but selection must remain explainable.").

Every candidate carries its per-factor breakdown alongside the final
score, so a ranking decision can always be explained rather than treated
as an opaque number.

Refinement over the literal formula: each factor is floored at
`MIN_FACTOR` rather than allowed to reach 0. A pure product would let any
single zero factor (e.g. a fully mastered concept's `weakness`) wipe out
the whole priority even when another factor (e.g. an overdue review)
argues strongly for surfacing it -- flooring keeps every factor's
influence visible in the breakdown instead of silently vanishing.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.entities import Concept
from app.domain.ports import (
    ClockPort,
    ConceptRelationRepository,
    ConceptRepository,
    EvidenceRepository,
    MistakeRepository,
)

MIN_FACTOR = 0.1
REVIEW_OVERDUE_PER_DAY = 1.0 / 30
REVIEW_OVERDUE_CAP = 3.0
MISTAKE_FACTOR_PER_OCCURRENCE = 0.2
MISTAKE_FACTOR_CAP = 2.0


@dataclass(frozen=True)
class ActivityCandidate:
    concept_id: str
    score: float
    breakdown: dict[str, float]


def _weakness(concept: Concept) -> float:
    return max(1.0 - concept.mastery / 5, MIN_FACTOR)


def _review_factor(concept: Concept, now: datetime) -> float:
    if concept.next_review is None:
        return 1.0
    if concept.next_review > now:
        return MIN_FACTOR
    overdue_days = (now - concept.next_review).total_seconds() / 86400
    return min(1.0 + overdue_days * REVIEW_OVERDUE_PER_DAY, REVIEW_OVERDUE_CAP)


class ActivitySelector:
    def __init__(
        self,
        concepts: ConceptRepository,
        concept_relations: ConceptRelationRepository,
        mistakes: MistakeRepository,
        evidence: EvidenceRepository,
        clock: ClockPort,
    ) -> None:
        self._concepts = concepts
        self._concept_relations = concept_relations
        self._mistakes = mistakes
        self._evidence = evidence
        self._clock = clock

    def rank(self, goal_id: str) -> list[ActivityCandidate]:
        now = self._clock.now()
        candidates = [self._score(concept, now) for concept in self._concepts.list_by_goal(goal_id)]
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    def _score(self, concept: Concept, now: datetime) -> ActivityCandidate:
        breakdown = {
            "importance": float(concept.importance),
            "weakness": _weakness(concept),
            "prerequisite_factor": self._prerequisite_factor(concept),
            "review_factor": _review_factor(concept, now),
            "mistake_factor": self._mistake_factor(concept),
            "transfer_factor": self._transfer_factor(concept),
        }
        score = 1.0
        for factor in breakdown.values():
            score *= factor
        return ActivityCandidate(concept_id=concept.id, score=score, breakdown=breakdown)

    def _prerequisite_factor(self, concept: Concept) -> float:
        prerequisites = self._concept_relations.list_prerequisites_of(concept.id)
        if not prerequisites:
            return 1.0
        masteries = [
            prerequisite.mastery
            for relation in prerequisites
            if (prerequisite := self._concepts.get(relation.source_id)) is not None
        ]
        if not masteries:
            return 1.0
        return max((sum(masteries) / len(masteries)) / 5, MIN_FACTOR)

    def _mistake_factor(self, concept: Concept) -> float:
        unresolved = sum(
            1 for m in self._mistakes.list_by_concept(concept.id) if m.resolved_at is None
        )
        return min(1.0 + MISTAKE_FACTOR_PER_OCCURRENCE * unresolved, MISTAKE_FACTOR_CAP)

    def _transfer_factor(self, concept: Concept) -> float:
        transfers = [
            e.transfer for e in self._evidence.list_by_concept(concept.id) if e.transfer is not None
        ]
        if not transfers:
            return 1.0
        return max(1.0 - sum(transfers) / len(transfers), MIN_FACTOR)
