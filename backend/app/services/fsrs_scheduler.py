"""FSRS scheduler -- optional `SchedulingStrategy` (docs/TASKS.md T130,
docs/SPECS.md #17: "MVP uses simple spaced repetition. Future versions
may use FSRS."). Implements the swap point `review_scheduler.py` (T063)
was built for: same `SchedulingStrategy` Protocol, so
`ReviewScheduler(clock, ids, strategy=FsrsScheduler())` is a drop-in
replacement for `SimpleSpacedRepetitionScheduler`.

Not wired in as the default -- `get_review_scheduler()`
(app/api/dependencies.py) still constructs the MVP strategy. Flipping the
production default would change every existing review's future interval
behavior, a product decision distinct from "the algorithm exists and is
available," the same boundary T129 drew around `ContextBuilder`
integration. Left for a dedicated future decision/task.

This is an independent reimplementation of the published FSRS-4.5
formulas (stability/difficulty memory model over a power-law forgetting
curve), not a vendored port of any specific FSRS library. Two
adaptations to this app's domain model were required:

1. FSRS grades reviews on a 4-point scale (Again/Hard/Good/Easy); this
   app only has a continuous `correctness` (0..1, docs/DOMAIN_MODEL.md
   #6, the same signal `SimpleSpacedRepetitionScheduler` uses). There is
   no separate "how hard was recall" UI. `_grade_from_correctness`
   buckets it into the 4 FSRS grades.
2. `SchedulingStrategy.next_interval(previous, correctness)` carries no
   clock, so the elapsed time since the previous review (needed for the
   retrievability estimate) is approximated as `previous.interval_days`
   (the gap that was actually scheduled) rather than actual elapsed
   wall-clock time.

A `previous` Review with `stability`/`difficulty` still `None` (i.e. its
own next-interval was computed by `SimpleSpacedRepetitionScheduler`, T063)
is treated the same as no history at all -- FSRS has no valid baseline to
continue from, so it bootstraps fresh via the first-review formulas.
"""

from dataclasses import dataclass
from math import exp
from typing import Final

from app.domain.entities import Review
from app.services.review_scheduler import MAX_INTERVAL_DAYS, MIN_INTERVAL_DAYS, SchedulingResult

MIN_STABILITY = 0.1
MIN_DIFFICULTY = 1.0
MAX_DIFFICULTY = 10.0
DEFAULT_REQUESTED_RETENTION = 0.9

DEFAULT_WEIGHTS: Final[tuple[float, ...]] = (
    0.4072,
    1.1829,
    3.1262,
    15.4722,
    7.2102,
    0.5316,
    1.0651,
    0.0234,
    1.616,
    0.1544,
    1.0824,
    1.9813,
    0.0953,
    0.2975,
    2.2042,
    0.2407,
    2.9466,
    0.5034,
    0.6567,
)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _grade_from_correctness(correctness: float) -> int:
    """Maps continuous `correctness` onto FSRS's 1..4 recall grade
    (1=Again, 2=Hard, 3=Good, 4=Easy). Boundaries mirror the MVP
    scheduler's own SUCCESS_THRESHOLD=0.6 split (below is a failed
    recall) with two extra buckets either side for FSRS's finer grading."""
    if correctness < 0.4:
        return 1
    if correctness < 0.6:
        return 2
    if correctness < 0.85:
        return 3
    return 4


@dataclass(frozen=True)
class FsrsScheduler:
    weights: tuple[float, ...] = DEFAULT_WEIGHTS
    requested_retention: float = DEFAULT_REQUESTED_RETENTION

    def next_interval(self, previous: Review | None, correctness: float) -> SchedulingResult:
        grade = _grade_from_correctness(correctness)
        w = self.weights

        if previous is None or previous.stability is None or previous.difficulty is None:
            stability = max(w[grade - 1], MIN_STABILITY)
            difficulty = _clamp(w[4] - (grade - 3) * w[5], MIN_DIFFICULTY, MAX_DIFFICULTY)
        else:
            elapsed_days = max(previous.interval_days, 0.1)
            retrievability = (1 + elapsed_days / (9 * previous.stability)) ** -1

            easy_baseline_difficulty = _clamp(w[4] - w[5], MIN_DIFFICULTY, MAX_DIFFICULTY)
            reverted_difficulty = previous.difficulty - w[6] * (grade - 3)
            difficulty = _clamp(
                w[7] * easy_baseline_difficulty + (1 - w[7]) * reverted_difficulty,
                MIN_DIFFICULTY,
                MAX_DIFFICULTY,
            )

            if grade == 1:
                stability = (
                    w[11]
                    * (difficulty ** -w[12])
                    * (((previous.stability + 1) ** w[13]) - 1)
                    * exp(w[14] * (1 - retrievability))
                )
            else:
                hard_penalty = w[15] if grade == 2 else 1.0
                easy_bonus = w[16] if grade == 4 else 1.0
                stability = previous.stability * (
                    1
                    + exp(w[8])
                    * (11 - difficulty)
                    * (previous.stability ** -w[9])
                    * (exp(w[10] * (1 - retrievability)) - 1)
                    * hard_penalty
                    * easy_bonus
                )
            stability = max(stability, MIN_STABILITY)

        interval_days = stability * 9 * (1 / self.requested_retention - 1)
        interval_days = _clamp(interval_days, MIN_INTERVAL_DAYS, MAX_INTERVAL_DAYS)

        return SchedulingResult(
            interval_days=interval_days, stability=stability, difficulty=difficulty
        )
