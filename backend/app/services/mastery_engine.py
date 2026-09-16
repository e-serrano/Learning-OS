"""Mastery engine -- computes `Concept.mastery`/`status` from `Evidence`
via the weighted formula in docs/DOMAIN_MODEL.md #18.

AI never assigns mastery directly (docs/DOMAIN_MODEL.md #4 invariant);
this is the only place mastery values are derived. Weights are
configuration, not business logic constants (docs/DOMAIN_MODEL.md #18),
so `MasteryWeights` is injectable rather than hardcoded inline.
"""

import math
from dataclasses import dataclass

from app.domain.entities import Concept, Evidence
from app.domain.enums import ConceptStatus
from app.domain.ports import EvidenceRepository

DEFAULT_RECENT_EVIDENCE_WINDOW = 5

WEAK_PERFORMANCE_THRESHOLD = 0.4
"""Below this recent-performance average, status becomes WEAK regardless
of the mastery tier -- see docs/DOMAIN_MODEL.md #17 ("weak evidence can
move a concept to weak or needs_review"; needs_review is driven by the
review scheduler, T063, not this engine)."""


@dataclass(frozen=True)
class MasteryWeights:
    recent_performance: float = 0.35
    historical_performance: float = 0.20
    transfer_performance: float = 0.20
    independence: float = 0.15
    retention: float = 0.10

    def __post_init__(self) -> None:
        total = (
            self.recent_performance
            + self.historical_performance
            + self.transfer_performance
            + self.independence
            + self.retention
        )
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"MasteryWeights must sum to 1.0, got {total}")


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _derive_status(mastery: float, recent_performance: float, has_evidence: bool) -> ConceptStatus:
    if not has_evidence:
        return ConceptStatus.UNKNOWN
    if recent_performance < WEAK_PERFORMANCE_THRESHOLD:
        return ConceptStatus.WEAK
    if mastery >= 4.0:
        return ConceptStatus.MASTERED
    if mastery >= 3.0:
        return ConceptStatus.STRONG
    if mastery >= 2.0:
        return ConceptStatus.USABLE
    if mastery >= 1.0:
        return ConceptStatus.DEVELOPING
    return ConceptStatus.LEARNING


class MasteryEngine:
    def __init__(
        self,
        evidence: EvidenceRepository,
        weights: MasteryWeights | None = None,
        recent_window: int = DEFAULT_RECENT_EVIDENCE_WINDOW,
    ) -> None:
        self._evidence = evidence
        self._weights = weights or MasteryWeights()
        self._recent_window = recent_window

    def compute(self, concept: Concept) -> Concept:
        """Returns a copy of `concept` with recalculated `mastery`/`status`.

        Never persists -- callers pass the result to
        `ConceptRepository.update()` themselves (docs/AGENTS.md: domain
        services do not own persistence)."""
        records: list[Evidence] = sorted(
            self._evidence.list_by_concept(concept.id), key=lambda e: e.timestamp
        )
        if not records:
            return concept.model_copy(update={"mastery": 0.0, "status": ConceptStatus.UNKNOWN})

        recent = records[-self._recent_window :]

        recent_performance = _average([e.correctness for e in recent if e.correctness is not None])
        historical_performance = _average(
            [e.correctness for e in records if e.correctness is not None]
        )
        transfer_performance = _average([e.transfer for e in records if e.transfer is not None])
        independence = _average([e.independence for e in records if e.independence is not None])
        retention = concept.retention / 100

        performance = (
            self._weights.recent_performance * recent_performance
            + self._weights.historical_performance * historical_performance
            + self._weights.transfer_performance * transfer_performance
            + self._weights.independence * independence
            + self._weights.retention * retention
        )
        mastery = round(min(max(performance, 0.0), 1.0) * 5, 2)
        status = _derive_status(mastery, recent_performance, has_evidence=True)

        return concept.model_copy(update={"mastery": mastery, "status": status})
