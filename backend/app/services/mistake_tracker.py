"""Mistake tracker -- groups normalized misconceptions and counts
recurrence (docs/TASKS.md T062, docs/DOMAIN_MODEL.md #10: "Recurring
mistakes must affect exercise selection").

AI evaluations only supply free-text misconception descriptions
(`EvaluatorResponse.misconceptions: list[str]`, docs/AI_CONTRACTS.md #8)
-- the same underlying misconception can be phrased differently across
attempts, so a naive exact-string match would undercount recurrence.
This tracker normalizes text (case/whitespace/punctuation) before
matching against existing `Mistake` rows for the concept. There is no
embeddings infrastructure in this MVP, so matching is normalized-exact,
not fuzzy/semantic -- see the same tradeoff made in `context_builder.py`
(T060).
"""

import re
import string

from app.domain.entities import Mistake
from app.domain.enums import MistakeSeverity, MistakeType
from app.domain.ports import ClockPort, IdGeneratorPort, MistakeRepository

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCTUATION_TABLE = str.maketrans("", "", string.punctuation)


def normalize(description: str) -> str:
    lowered = description.lower().translate(_PUNCTUATION_TABLE)
    return _WHITESPACE_RE.sub(" ", lowered).strip()


class MistakeTracker:
    def __init__(
        self,
        mistakes: MistakeRepository,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._mistakes = mistakes
        self._clock = clock
        self._ids = ids

    def record(
        self,
        concept_id: str,
        goal_id: str,
        description: str,
        type: MistakeType = MistakeType.MISCONCEPTION,
        severity: MistakeSeverity = MistakeSeverity.MEDIUM,
    ) -> Mistake:
        """Records one observed mistake, merging into an existing row when
        its normalized description already matches one for this concept
        -- otherwise creates a new one. A match reopens a previously
        resolved mistake, since its recurrence is new evidence it was not
        actually resolved."""
        target = normalize(description)
        now = self._clock.now()

        for existing in self._mistakes.list_by_concept(concept_id):
            if normalize(existing.description) == target:
                updated = existing.model_copy(
                    update={
                        "occurrences": existing.occurrences + 1,
                        "last_seen": now,
                        "resolved_at": None,
                    }
                )
                self._mistakes.update(updated)
                return updated

        created = Mistake(
            id=self._ids.new_id("mistake"),
            concept_id=concept_id,
            goal_id=goal_id,
            type=type,
            description=description,
            severity=severity,
            occurrences=1,
            first_seen=now,
            last_seen=now,
        )
        self._mistakes.add(created)
        return created
