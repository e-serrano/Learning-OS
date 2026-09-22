from datetime import UTC, datetime, timedelta

from app.domain.entities import Mistake
from app.domain.enums import MistakeSeverity, MistakeType
from app.services.mistake_tracker import MistakeTracker, normalize

NOW = datetime.now(UTC)
LATER = NOW + timedelta(hours=1)


class FakeMistakeRepository:
    def __init__(self) -> None:
        self._rows: dict[str, Mistake] = {}

    def add(self, mistake: Mistake) -> None:
        self._rows[mistake.id] = mistake

    def list_by_concept(self, concept_id: str) -> list[Mistake]:
        return [m for m in self._rows.values() if m.concept_id == concept_id]

    def update(self, mistake: Mistake) -> None:
        self._rows[mistake.id] = mistake


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


def test_normalize_collapses_case_whitespace_and_punctuation() -> None:
    assert normalize("Confuses  ROW_NUMBER, and RANK!") == normalize("confuses row_number and rank")


def test_first_occurrence_creates_a_new_mistake() -> None:
    tracker = MistakeTracker(FakeMistakeRepository(), FakeClock(NOW), FakeIdGenerator())

    result = tracker.record("concept_1", "goal_1", "Confuses ROW_NUMBER and RANK")

    assert result.occurrences == 1
    assert result.first_seen == NOW
    assert result.last_seen == NOW
    assert result.type == MistakeType.MISCONCEPTION
    assert result.severity == MistakeSeverity.MEDIUM


def test_recurring_normalized_description_increments_occurrences() -> None:
    mistakes = FakeMistakeRepository()
    tracker = MistakeTracker(mistakes, FakeClock(NOW), FakeIdGenerator())
    first = tracker.record("concept_1", "goal_1", "Confuses ROW_NUMBER and RANK.")

    tracker_later = MistakeTracker(mistakes, FakeClock(LATER), FakeIdGenerator())
    second = tracker_later.record("concept_1", "goal_1", "confuses row_number and rank")

    assert second.id == first.id
    assert second.occurrences == 2
    assert second.last_seen == LATER
    assert len(mistakes.list_by_concept("concept_1")) == 1


def test_differently_worded_but_equivalent_text_still_matches() -> None:
    mistakes = FakeMistakeRepository()
    tracker = MistakeTracker(mistakes, FakeClock(NOW), FakeIdGenerator())
    tracker.record("concept_1", "goal_1", "Forgets PARTITION BY in window functions")
    result = tracker.record("concept_1", "goal_1", "forgets partition by in window functions!!")

    assert result.occurrences == 2


def test_different_misconceptions_create_separate_rows() -> None:
    mistakes = FakeMistakeRepository()
    tracker = MistakeTracker(mistakes, FakeClock(NOW), FakeIdGenerator())
    tracker.record("concept_1", "goal_1", "Confuses ROW_NUMBER and RANK")
    tracker.record("concept_1", "goal_1", "Forgets PARTITION BY")

    assert len(mistakes.list_by_concept("concept_1")) == 2


def test_same_description_in_different_concepts_creates_separate_rows() -> None:
    mistakes = FakeMistakeRepository()
    tracker = MistakeTracker(mistakes, FakeClock(NOW), FakeIdGenerator())
    tracker.record("concept_1", "goal_1", "Off by one error")
    tracker.record("concept_2", "goal_1", "Off by one error")

    assert len(mistakes.list_by_concept("concept_1")) == 1
    assert len(mistakes.list_by_concept("concept_2")) == 1


def test_recurrence_reopens_a_resolved_mistake() -> None:
    mistakes = FakeMistakeRepository()
    mistakes.add(
        Mistake(
            id="mistake_1",
            concept_id="concept_1",
            goal_id="goal_1",
            type=MistakeType.MISCONCEPTION,
            description="Confuses ROW_NUMBER and RANK",
            severity=MistakeSeverity.MEDIUM,
            occurrences=1,
            first_seen=NOW,
            last_seen=NOW,
            resolved_at=NOW,
        )
    )
    tracker = MistakeTracker(mistakes, FakeClock(LATER), FakeIdGenerator())

    result = tracker.record("concept_1", "goal_1", "confuses row_number and rank")

    assert result.id == "mistake_1"
    assert result.occurrences == 2
    assert result.resolved_at is None


def test_caller_can_override_type_and_severity() -> None:
    tracker = MistakeTracker(FakeMistakeRepository(), FakeClock(NOW), FakeIdGenerator())

    result = tracker.record(
        "concept_1",
        "goal_1",
        "Times out on large inputs",
        type=MistakeType.PROCEDURE,
        severity=MistakeSeverity.HIGH,
    )

    assert result.type == MistakeType.PROCEDURE
    assert result.severity == MistakeSeverity.HIGH
