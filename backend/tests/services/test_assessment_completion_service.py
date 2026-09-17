from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import EvaluatorResponse
from app.ai.orchestrator import AIOrchestrator
from app.domain.entities import Evaluation, Evidence, Exercise, ExerciseAttempt, Session
from app.domain.enums import ExerciseType, SessionMode, SessionStatus
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.services.answer_submission_service import AnswerSubmissionService
from app.services.assessment_completion_service import AssessmentCompletionService
from app.services.evaluator_service import EvaluatorService
from app.services.evidence_creation_service import EvidenceCreationService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeExerciseRepository:
    def __init__(self, exercises: list[Exercise]) -> None:
        self._by_id = {e.id: e for e in exercises}

    def get(self, exercise_id: str) -> Exercise | None:
        return self._by_id.get(exercise_id)

    def add(self, exercise: Exercise) -> None:
        self._by_id[exercise.id] = exercise


class FakeSessionRepository:
    def __init__(self, sessions: list[Session]) -> None:
        self._by_id = {s.id: s for s in sessions}

    def get(self, session_id: str) -> Session | None:
        return self._by_id.get(session_id)

    def add(self, session: Session) -> None:
        self._by_id[session.id] = session

    def update(self, session: Session) -> None:
        self._by_id[session.id] = session


class FakeExerciseAttemptRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, ExerciseAttempt] = {}

    def add(self, attempt: ExerciseAttempt) -> None:
        self._by_id[attempt.id] = attempt

    def get(self, attempt_id: str) -> ExerciseAttempt | None:
        return self._by_id.get(attempt_id)


class FakeEvaluationRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, Evaluation] = {}

    def add(self, evaluation: Evaluation) -> None:
        self._by_id[evaluation.id] = evaluation

    def get(self, evaluation_id: str) -> Evaluation | None:
        return self._by_id.get(evaluation_id)


class FakeEvidenceRepository:
    def __init__(self) -> None:
        self.added: list[Evidence] = []

    def add(self, evidence: Evidence) -> None:
        self.added.append(evidence)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class FakeIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _exercise(**overrides: object) -> Exercise:
    defaults: dict[str, object] = dict(
        id="exercise_1",
        type=ExerciseType.SCENARIO,
        difficulty=4,
        goal_id="goal_1",
        concept_ids=["window_functions"],
        prompt="Rank shipments per warehouse.",
        solution="SELECT RANK() OVER (...) FROM shipments;",
        created_at=NOW,
    )
    defaults.update(overrides)
    return Exercise(**defaults)  # type: ignore[arg-type]


def _session(**overrides: object) -> Session:
    defaults: dict[str, object] = dict(
        id="session_1",
        goal_id="goal_1",
        mode=SessionMode.ASSESSMENT,
        objective="Transfer check",
        status=SessionStatus.ACTIVE,
        started_at=NOW,
    )
    defaults.update(overrides)
    return Session(**defaults)  # type: ignore[arg-type]


def _service(tmp_path: Path, provider: object) -> AssessmentCompletionService:
    engine = _engine(tmp_path)
    exercises = FakeExerciseRepository([_exercise()])
    sessions = FakeSessionRepository([_session()])
    attempts = FakeExerciseAttemptRepository()
    evaluations = FakeEvaluationRepository()
    evidence = FakeEvidenceRepository()
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]

    answer_submission = AnswerSubmissionService(
        exercises, sessions, attempts, FakeClock(), FakeIdGenerator()
    )
    evaluator = EvaluatorService(
        attempts, exercises, evaluations, orchestrator, FakeClock(), FakeIdGenerator()
    )
    evidence_creation = EvidenceCreationService(
        evaluations, attempts, exercises, evidence, FakeClock(), FakeIdGenerator()
    )
    return AssessmentCompletionService(answer_submission, evaluator, evidence_creation)


def _evaluator_response(**overrides: object) -> EvaluatorResponse:
    defaults: dict[str, object] = dict(
        correctness=0.9,
        reasoning=0.8,
        completeness=0.7,
        independence=0.8,
        transfer=0.8,
        feedback="Applied it well to the new domain.",
        recommended_action="advance",
    )
    defaults.update(overrides)
    return EvaluatorResponse(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_complete_assessment_runs_the_full_pipeline(tmp_path: Path) -> None:
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _evaluator_response())
    service = _service(tmp_path, provider)

    result = await service.complete_assessment(
        "exercise_1", "session_1", "activity_1", "my answer", confidence=80
    )

    assert result.attempt.exercise_id == "exercise_1"
    assert result.evaluation.attempt_id == result.attempt.id
    assert [e.concept_id for e in result.evidence] == ["window_functions"]


@pytest.mark.asyncio
async def test_transfer_and_independence_demonstrated_above_threshold(tmp_path: Path) -> None:
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _evaluator_response(transfer=0.8, independence=0.7))
    service = _service(tmp_path, provider)

    result = await service.complete_assessment(
        "exercise_1", "session_1", "activity_1", "my answer", confidence=80
    )

    assert result.transfer_demonstrated is True
    assert result.independence_demonstrated is True


@pytest.mark.asyncio
async def test_transfer_and_independence_not_demonstrated_below_threshold(tmp_path: Path) -> None:
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _evaluator_response(transfer=0.3, independence=0.2))
    service = _service(tmp_path, provider)

    result = await service.complete_assessment(
        "exercise_1", "session_1", "activity_1", "my answer", confidence=50
    )

    assert result.transfer_demonstrated is False
    assert result.independence_demonstrated is False


@pytest.mark.asyncio
async def test_threshold_boundary_counts_as_demonstrated(tmp_path: Path) -> None:
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _evaluator_response(transfer=0.6, independence=0.6))
    service = _service(tmp_path, provider)

    result = await service.complete_assessment(
        "exercise_1", "session_1", "activity_1", "my answer", confidence=80
    )

    assert result.transfer_demonstrated is True
    assert result.independence_demonstrated is True
