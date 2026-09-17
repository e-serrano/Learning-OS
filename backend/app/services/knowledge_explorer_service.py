"""Knowledge explorer -- read-only concept listing/detail/relations for
a goal (docs/TASKS.md T100, docs/API_SPEC.md #3).

No live mastery computation here: `Concept.mastery`/`.status`/
`.next_review` are the materialized values `MasteryUpdateService` (T062)
and `RetentionUpdateService` keep current after every evidence event --
this only reads and filters them.
"""

from datetime import datetime

from app.domain.entities import Concept, ConceptRelation
from app.domain.enums import ConceptStatus
from app.domain.ports import ConceptRelationRepository, ConceptRepository, GoalRepository
from app.services.context_builder import ConceptNotFoundError, GoalNotFoundError

__all__ = ["ConceptNotFoundError", "GoalNotFoundError", "KnowledgeExplorerService"]


class KnowledgeExplorerService:
    def __init__(
        self,
        goals: GoalRepository,
        concepts: ConceptRepository,
        relations: ConceptRelationRepository,
    ) -> None:
        self._goals = goals
        self._concepts = concepts
        self._relations = relations

    def list_concepts(
        self,
        goal_id: str,
        status: ConceptStatus | None = None,
        mastery_lt: float | None = None,
        next_review_before: datetime | None = None,
    ) -> list[Concept]:
        if self._goals.get(goal_id) is None:
            raise GoalNotFoundError(goal_id)

        concepts = self._concepts.list_by_goal(goal_id)
        if status is not None:
            concepts = [c for c in concepts if c.status == status]
        if mastery_lt is not None:
            concepts = [c for c in concepts if c.mastery < mastery_lt]
        if next_review_before is not None:
            concepts = [
                c
                for c in concepts
                if c.next_review is not None and c.next_review < next_review_before
            ]
        return concepts

    def get_concept(self, concept_id: str) -> Concept:
        concept = self._concepts.get(concept_id)
        if concept is None:
            raise ConceptNotFoundError(concept_id)
        return concept

    def list_relations(self, concept_id: str) -> list[ConceptRelation]:
        self.get_concept(concept_id)
        return self._relations.list_relations_from(concept_id)
