"""Review scheduler -- deterministic MVP spaced repetition (docs/TASKS.md
T063, docs/SPECS.md #17: "MVP uses simple spaced repetition. Future
versions may use FSRS.").

The scheduling algorithm sits behind `SchedulingStrategy`, a swap point
that `FsrsScheduler` (app/services/fsrs_scheduler.py, docs/TASKS.md T130)
now implements: same Protocol, reads `previous.stability`/
`previous.difficulty` (already present on the `Review` entity, unused by
this MVP strategy) -- no other caller changes needed. Not the wired-in
default yet; see `fsrs_scheduler.py`'s module docstring for why.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from app.domain.entities import Review
from app.domain.enums import ReviewStatus
from app.domain.ports import ClockPort, IdGeneratorPort

INITIAL_INTERVAL_DAYS = 1.0
MIN_INTERVAL_DAYS = 1.0
MAX_INTERVAL_DAYS = 180.0
GROWTH_FACTOR = 2.0
SUCCESS_THRESHOLD = 0.6


@dataclass(frozen=True)
class SchedulingResult:
    interval_days: float
    stability: float | None = None
    difficulty: float | None = None


class SchedulingStrategy(Protocol):
    def next_interval(self, previous: Review | None, correctness: float) -> SchedulingResult: ...


class SimpleSpacedRepetitionScheduler:
    """MVP strategy -- see docs/SPECS.md #17. Deterministic: grows the
    interval geometrically after a successful recall, resets to the floor
    after a failed one. Never sets stability/difficulty -- those are
    FSRS-only concepts this strategy has no use for."""

    def next_interval(self, previous: Review | None, correctness: float) -> SchedulingResult:
        if previous is None:
            return SchedulingResult(interval_days=INITIAL_INTERVAL_DAYS)
        if correctness >= SUCCESS_THRESHOLD:
            grown = previous.interval_days * GROWTH_FACTOR
            return SchedulingResult(interval_days=min(grown, MAX_INTERVAL_DAYS))
        return SchedulingResult(interval_days=MIN_INTERVAL_DAYS)


class ReviewScheduler:
    def __init__(
        self,
        clock: ClockPort,
        ids: IdGeneratorPort,
        strategy: SchedulingStrategy | None = None,
    ) -> None:
        self._clock = clock
        self._ids = ids
        self._strategy = strategy or SimpleSpacedRepetitionScheduler()

    def schedule_next(
        self,
        concept_id: str,
        goal_id: str,
        correctness: float,
        previous: Review | None = None,
    ) -> Review:
        """Returns the next scheduled Review. Never persists -- callers
        pass the result to `ReviewRepository.add()` themselves."""
        result = self._strategy.next_interval(previous, correctness)
        now = self._clock.now()
        return Review(
            id=self._ids.new_id("review"),
            concept_id=concept_id,
            goal_id=goal_id,
            scheduled_at=now + timedelta(days=result.interval_days),
            interval_days=result.interval_days,
            stability=result.stability,
            difficulty=result.difficulty,
            status=ReviewStatus.SCHEDULED,
        )
