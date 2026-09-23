"""Derived mastery update -- recomputes and persists Concept.mastery
after new Evidence (docs/TASKS.md T075).

Thin wiring: `MasteryEngine.compute()` (T061) never persists by design
-- this service is the one place that takes its result and calls
`ConceptRepository.update()`.

Also the one place that can detect a genuine mastery *transition* (old
status vs. newly computed status) -- it already reads the concept before
computing the update, so triggering `MasteryCurationTriggerService`
(T139, optional -- `None` when no vault/AI provider is configured) right
here, rather than duplicating "read old status, call update_mastery,
compare" in every one of its four callers (`AnswerFlowService`,
`AssessmentFlowService`, `ProjectFlowService`, `ReviewFlowService`),
keeps it in exactly one place.
"""

from app.domain.entities import Concept
from app.domain.ports import ConceptRepository
from app.services.context_builder import ConceptNotFoundError
from app.services.mastery_curation_trigger_service import MasteryCurationTriggerService
from app.services.mastery_engine import MasteryEngine


class MasteryUpdateService:
    def __init__(
        self,
        concepts: ConceptRepository,
        mastery_engine: MasteryEngine,
        curation_trigger: MasteryCurationTriggerService | None = None,
    ) -> None:
        self._concepts = concepts
        self._mastery_engine = mastery_engine
        self._curation_trigger = curation_trigger

    async def update_mastery(self, concept_id: str, goal_id: str) -> Concept:
        concept = self._concepts.get(concept_id)
        if concept is None:
            raise ConceptNotFoundError(concept_id)

        updated = self._mastery_engine.compute(concept)
        self._concepts.update(updated)

        if self._curation_trigger is not None:
            await self._curation_trigger.trigger_if_newly_mastered(goal_id, concept.status, updated)

        return updated
