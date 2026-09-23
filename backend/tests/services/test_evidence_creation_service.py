from datetime import UTC, datetime

import pytest

from app.domain.entities import Evaluation, Evidence, Exercise, ExerciseAttempt
from app.domain.enums import EvidenceSourceType, ExerciseType
from app.services.answer_submission_service import ExerciseNotFoundError
from app.services.evaluator_service import AttemptNotFoundError
from app.services.evidence_creation_service import (
    EvaluationNotFoundError,
    EvidenceCreationService,
)

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


class FakeEvidenceRepository:
    def __init__(self) -> None:
        self.added: list[Evidence] = []

    def add(self, evidence: Evidence) -> None:
        self.added.append(evidence)

    def list_by_concept(self, concept_id: str) -> list[Evidence]:
        return [e for e in self.added if e.concept_id == concept_id]

    def list_by_goal(self, goal_id: str) -> list[Evidence]:
        return [e for e in self.added if e.goal_id == goal_id]


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
        correctness=0.9,
        reasoning=0.8,
        completeness=0.7,
        independence=0.6,
        transfer=0.5,
        feedback="Good",
        recommended_action="advance",
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
) -> tuple[EvidenceCreationService, FakeEvidenceRepository]:
    evidence_repo = FakeEvidenceRepository()
    service = EvidenceCreationService(
        FakeEvaluationRepository(evaluations if evaluations is not None else [_evaluation()]),
        FakeExerciseAttemptRepository(attempts if attempts is not None else [_attempt()]),
        FakeExerciseRepository(exercises if exercises is not None else [_exercise()]),
        evidence_repo,
        FakeClock(NOW),
        FakeIdGenerator(),
    )
    return service, evidence_repo


def test_create_evidence_maps_evaluation_scores_onto_evidence() -> None:
    service, _ = _service()

    [evidence] = service.create_evidence("evaluation_1", activity_id="activity_1")

    assert evidence.concept_id == "concept_1"
    assert evidence.goal_id == "goal_1"
    assert evidence.session_id == "session_1"
    assert evidence.activity_id == "activity_1"
    assert evidence.source_type == EvidenceSourceType.EXERCISE
    assert evidence.difficulty == 3
    assert evidence.correctness == 0.9
    assert evidence.reasoning == 0.8
    assert evidence.independence == 0.6
    assert evidence.transfer == 0.5
    assert evidence.timestamp == NOW


def test_create_evidence_converts_confidence_percent_to_normalized_score() -> None:
    service, _ = _service(attempts=[_attempt(confidence=80)])

    [evidence] = service.create_evidence("evaluation_1", activity_id="activity_1")

    assert evidence.confidence == 0.8


def test_create_evidence_records_traceability_metadata() -> None:
    service, _ = _service()

    [evidence] = service.create_evidence("evaluation_1", activity_id="activity_1")

    assert evidence.metadata == {"evaluation_id": "evaluation_1", "attempt_id": "attempt_1"}


def test_create_evidence_persists_via_evidence_repository() -> None:
    service, evidence_repo = _service()

    created = service.create_evidence("evaluation_1", activity_id="activity_1")

    assert evidence_repo.added == created


def test_create_evidence_fans_out_one_row_per_concept() -> None:
    service, _ = _service(exercises=[_exercise(concept_ids=["concept_1", "concept_2"])])

    created = service.create_evidence("evaluation_1", activity_id="activity_1")

    assert {e.concept_id for e in created} == {"concept_1", "concept_2"}
    assert len(created) == 2


def test_create_evidence_raises_when_evaluation_not_found() -> None:
    service, evidence_repo = _service(evaluations=[])

    with pytest.raises(EvaluationNotFoundError):
        service.create_evidence("missing_evaluation", activity_id="activity_1")

    assert evidence_repo.added == []


def test_create_evidence_raises_when_attempt_not_found() -> None:
    service, evidence_repo = _service(attempts=[])

    with pytest.raises(AttemptNotFoundError):
        service.create_evidence("evaluation_1", activity_id="activity_1")

    assert evidence_repo.added == []


def test_create_evidence_raises_when_exercise_not_found() -> None:
    service, evidence_repo = _service(exercises=[])

    with pytest.raises(ExerciseNotFoundError):
        service.create_evidence("evaluation_1", activity_id="activity_1")

    assert evidence_repo.added == []


def test_create_evidence_tags_teach_back_exercises_with_their_own_source_type() -> None:
    service, _ = _service(exercises=[_exercise(type=ExerciseType.TEACH_BACK)])

    [evidence] = service.create_evidence("evaluation_1", activity_id="activity_1")

    assert evidence.source_type == EvidenceSourceType.TEACH_BACK


def test_create_evidence_keeps_the_exercise_source_type_for_every_other_type() -> None:
    for exercise_type in ExerciseType:
        if exercise_type == ExerciseType.TEACH_BACK:
            continue
        service, _ = _service(exercises=[_exercise(type=exercise_type)])

        [evidence] = service.create_evidence("evaluation_1", activity_id="activity_1")

        assert evidence.source_type == EvidenceSourceType.EXERCISE
