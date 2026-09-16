"""Derived mastery update -- recomputes and persists Concept.mastery
after new Evidence (docs/TASKS.md T075).

Thin wiring: `MasteryEngine.compute()` (T061) never persists by design
-- this service is the one place that takes its result and calls
`ConceptRepository.update()`.
"""

from app.domain.entities import Concept
from app.domain.ports import ConceptRepository
from app.services.context_builder import ConceptNotFoundError
from app.services.mastery_engine import MasteryEngine


class MasteryUpdateService:
    def __init__(self, concepts: ConceptRepository, mastery_engine: MasteryEngine) -> None:
        self._concepts = concepts
        self._mastery_engine = mastery_engine

    def update_mastery(self, concept_id: str) -> Concept:
        concept = self._concepts.get(concept_id)
        if concept is None:
            raise ConceptNotFoundError(concept_id)

        updated = self._mastery_engine.compute(concept)
        self._concepts.update(updated)
        return updated
