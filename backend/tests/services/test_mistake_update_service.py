from datetime import UTC, datetime

import pytest

from app.domain.entities import Evaluation, Exercise, ExerciseAttempt, Mistake
from app.domain.enums import ExerciseType
from app.services.answer_submission_service import ExerciseNotFoundError
from app.services.evaluator_service import AttemptNotFoundError
from app.services.evidence_creation_service import EvaluationNotFoundError
from app.services.mistake_tracker import MistakeTracker
from app.services.mistake_update_service import MistakeUpdateService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeEvaluationRepository:
    def __init__(self, evaluations: list[Evaluation]) -> None:
        self._by_id = {e.id: e for e in evaluations}

    def get(self, evaluation_id: str) -> Evaluation | None:
        return self._by_id.get(evaluation_id)

    def add(self, evaluation: Evaluation) -> None:
        self._by_id[evaluation.id] = evaluation


class FakeExerciseAttemptRepository:
    def __init__(self, attempts: list[ExerciseAttempt]) -> None:
        self._by_id = {a.id: a for a in attempts}

    def get(self, attempt_id: str) -> ExerciseAttempt | None:
        return self._by_id.get(attempt_id)

    def add(self, attempt: ExerciseAttempt) -> None:
        self._by_id[attempt.id] = attempt


class FakeExerciseRepository:
    def __init__(self, exercises: list[Exercise]) -> None:
        self._by_id = {e.id: e for e in exercises}

    def get(self, exercise_id: str) -> Exercise | None:
        return self._by_id.get(exercise_id)

    def add(self, exercise: Exercise) -> None:
        self._by_id[exercise.id] = exercise


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
    def now(self) -> datetime:
        return NOW


class FakeIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


def _exercise(**overrides: object) -> Exercise:
    defaults: dict[str, object] = dict(
        id="exercise_1",
        type=ExerciseType.SQL,
        difficulty=3,
        goal_id="goal_1",
        concept_ids=["concept_1"],
        prompt="Write a query",
        solution="SELECT 1",
        created_at=NOW,
    )
    defaults.update(overrides)
    return Exercise(**defaults)  # type: ignore[arg-type]


def _attempt(**overrides: object) -> ExerciseAttempt:
    defaults: dict[str, object] = dict(
        id="attempt_1",
        exercise_id="exercise_1",
        session_id="session_1",
        answer="SELECT 1;",
        confidence=80,
        submitted_at=NOW,
    )
    defaults.update(overrides)
    return ExerciseAttempt(**defaults)  # type: ignore[arg-type]


def _evaluation(**overrides: object) -> Evaluation:
    defaults: dict[str, object] = dict(
        id="evaluation_1",
        attempt_id="attempt_1",
        correctness=0.5,
        reasoning=0.5,
        completeness=0.5,
        independence=0.5,
        transfer=0.5,
        misconceptions=["Confuses ROW_NUMBER and RANK"],
        feedback="...",
        recommended_action="review",
        provider="mock",
        model="mock-1",
        prompt_version="evaluator.v1",
        created_at=NOW,
    )
    defaults.update(overrides)
    return Evaluation(**defaults)  # type: ignore[arg-type]


def _service(
    evaluations: list[Evaluation] | None = None,
    attempts: list[ExerciseAttempt] | None = None,
    exercises: list[Exercise] | None = None,
) -> tuple[MistakeUpdateService, FakeMistakeRepository]:
    mistakes = FakeMistakeRepository()
    tracker = MistakeTracker(mistakes, FakeClock(), FakeIdGenerator())
    service = MistakeUpdateService(
        FakeEvaluationRepository(evaluations if evaluations is not None else [_evaluation()]),
        FakeExerciseAttemptRepository(attempts if attempts is not None else [_attempt()]),
        FakeExerciseRepository(exercises if exercises is not None else [_exercise()]),
        tracker,
    )
    return service, mistakes


def test_records_a_mistake_for_each_misconception() -> None:
    service, mistakes = _service()

    recorded = service.record_from_evaluation("evaluation_1")

    assert len(recorded) == 1
    assert recorded[0].concept_id == "concept_1"
    assert recorded[0].goal_id == "goal_1"
    assert recorded[0].description == "Confuses ROW_NUMBER and RANK"
    assert mistakes.list_by_concept("concept_1") == recorded


def test_recurring_misconception_increments_instead_of_duplicating() -> None:
    service, mistakes = _service()
    service.record_from_evaluation("evaluation_1")

    second = service.record_from_evaluation("evaluation_1")

    assert second[0].occurrences == 2
    assert len(mistakes.list_by_concept("concept_1")) == 1


def test_returns_empty_list_when_no_misconceptions_reported() -> None:
    service, mistakes = _service(evaluations=[_evaluation(misconceptions=[])])

    recorded = service.record_from_evaluation("evaluation_1")

    assert recorded == []
    assert mistakes.list_by_concept("concept_1") == []


def test_fans_out_across_multiple_concepts() -> None:
    service, mistakes = _service(exercises=[_exercise(concept_ids=["concept_1", "concept_2"])])

    recorded = service.record_from_evaluation("evaluation_1")

    assert {m.concept_id for m in recorded} == {"concept_1", "concept_2"}


def test_raises_when_evaluation_not_found() -> None:
    service, _ = _service(evaluations=[])

    with pytest.raises(EvaluationNotFoundError):
        service.record_from_evaluation("missing_evaluation")


def test_raises_when_attempt_not_found() -> None:
    service, _ = _service(attempts=[])

    with pytest.raises(AttemptNotFoundError):
        service.record_from_evaluation("evaluation_1")


def test_raises_when_exercise_not_found() -> None:
    service, _ = _service(exercises=[])

    with pytest.raises(ExerciseNotFoundError):
        service.record_from_evaluation("evaluation_1")
