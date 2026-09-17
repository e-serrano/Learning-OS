"""Retention update -- recomputes and persists `Concept.retention` from
review evidence (docs/TASKS.md T088).

Retention specifically measures recall after a gap without practice --
exactly what a spaced-repetition review tests (T063/T077's
`EvidenceSourceType.REVIEW`), unlike regular exercise evidence, which
tests immediate application. `MasteryEngine` (T061) already reads
`Concept.retention` as one of its five inputs; this is the one place
that writes it, closing that loop.
"""

from app.domain.entities import Concept
from app.domain.enums import EvidenceSourceType
from app.domain.ports import ConceptRepository, EvidenceRepository
from app.services.context_builder import ConceptNotFoundError

DEFAULT_RECENT_REVIEW_WINDOW = 5


class RetentionUpdateService:
    def __init__(
        self,
        concepts: ConceptRepository,
        evidence: EvidenceRepository,
        recent_window: int = DEFAULT_RECENT_REVIEW_WINDOW,
    ) -> None:
        self._concepts = concepts
        self._evidence = evidence
        self._recent_window = recent_window

    def update_retention(self, concept_id: str) -> Concept:
        concept = self._concepts.get(concept_id)
        if concept is None:
            raise ConceptNotFoundError(concept_id)

        recent_reviews = sorted(
            (
                e
                for e in self._evidence.list_by_concept(concept_id)
                if e.source_type == EvidenceSourceType.REVIEW
            ),
            key=lambda e: e.timestamp,
            reverse=True,
        )[: self._recent_window]

        scores = [e.correctness for e in recent_reviews if e.correctness is not None]
        if not scores:
            # No review evidence to derive retention from -- retention
            # decaying over time isn't modeled here, so leave it as-is
            # rather than clobbering it with an arbitrary value.
            return concept

        retention = round((sum(scores) / len(scores)) * 100, 2)
        updated = concept.model_copy(update={"retention": retention})
        self._concepts.update(updated)
        return updated
