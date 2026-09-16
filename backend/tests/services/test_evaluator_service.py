from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import EvaluatorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Evaluation, Exercise, ExerciseAttempt
from app.domain.enums import ExerciseType
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.services.answer_submission_service import ExerciseNotFoundError
from app.services.evaluator_service import AttemptNotFoundError, EvaluatorService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


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


class FakeEvaluationRepository:
    def __init__(self) -> None:
        self.added: list[Evaluation] = []

    def add(self, evaluation: Evaluation) -> None:
        self.added.append(evaluation)

    def get(self, evaluation_id: str) -> Evaluation | None:
        return next((e for e in self.added if e.id == evaluation_id), None)


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


class NeverCalledProvider:
    async def generate(self, request: object, response_model: object) -> object:
        raise AssertionError("AI provider must not be called")


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _exercise(**overrides: object) -> Exercise:
    defaults: dict[str, object] = dict(
        id="exercise_1",
        type=ExerciseType.SQL,
        difficulty=3,
        goal_id="goal_1",
        prompt="Write a query using ROW_NUMBER().",
        solution="SELECT ROW_NUMBER() OVER (...) FROM t;",
        success_criteria=["Uses ROW_NUMBER()"],
        created_at=NOW,
    )
    defaults.update(overrides)
    return Exercise(**defaults)  # type: ignore[arg-type]


def _attempt(**overrides: object) -> ExerciseAttempt:
    defaults: dict[str, object] = dict(
        id="attempt_1",
        exercise_id="exercise_1",
        session_id="session_1",
        answer="SELECT ROW_NUMBER() OVER (ORDER BY id) FROM t;",
        confidence=72,
        submitted_at=NOW,
    )
    defaults.update(overrides)
    return ExerciseAttempt(**defaults)  # type: ignore[arg-type]


def _evaluator_response(**overrides: object) -> EvaluatorResponse:
    defaults: dict[str, object] = dict(
        correctness=0.9,
        reasoning=0.8,
        completeness=0.7,
        independence=0.6,
        transfer=0.5,
        misconceptions=["Forgets ORDER BY inside OVER()"],
        feedback="Mostly correct.",
        recommended_action="review_transfer",
    )
    defaults.update(overrides)
    return EvaluatorResponse(**defaults)  # type: ignore[arg-type]


def _service(
    engine: Engine,
    provider: object,
    attempts: list[ExerciseAttempt] | None = None,
    exercises: list[Exercise] | None = None,
) -> tuple[EvaluatorService, FakeEvaluationRepository]:
    evaluations = FakeEvaluationRepository()
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    service = EvaluatorService(
        attempts=FakeExerciseAttemptRepository(attempts if attempts is not None else [_attempt()]),
        exercises=FakeExerciseRepository(exercises if exercises is not None else [_exercise()]),
        evaluations=evaluations,
        orchestrator=orchestrator,
        clock=FakeClock(NOW),
        ids=FakeIdGenerator(),
    )
    return service, evaluations


@pytest.mark.asyncio
async def test_evaluate_returns_evaluation_built_from_ai_response(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _evaluator_response())
    service, _ = _service(engine, provider)

    evaluation = await service.evaluate("attempt_1")

    assert evaluation.attempt_id == "attempt_1"
    assert evaluation.correctness == 0.9
    assert evaluation.reasoning == 0.8
    assert evaluation.completeness == 0.7
    assert evaluation.independence == 0.6
    assert evaluation.transfer == 0.5
    assert evaluation.misconceptions == ["Forgets ORDER BY inside OVER()"]
    assert evaluation.feedback == "Mostly correct."
    assert evaluation.recommended_action == "review_transfer"
    assert evaluation.provider == "mock"
    assert evaluation.model == "mock-1"
    assert evaluation.prompt_version == "evaluator.v1"
    assert evaluation.created_at == NOW


@pytest.mark.asyncio
async def test_evaluate_persists_via_evaluation_repository(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _evaluator_response())
    service, evaluations = _service(engine, provider)

    created = await service.evaluate("attempt_1")

    assert evaluations.added == [created]


@pytest.mark.asyncio
async def test_evaluate_raises_when_attempt_not_found_without_calling_ai(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service, _ = _service(engine, NeverCalledProvider(), attempts=[])

    with pytest.raises(AttemptNotFoundError):
        await service.evaluate("missing_attempt")


@pytest.mark.asyncio
async def test_evaluate_raises_when_exercise_not_found_without_calling_ai(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    service, _ = _service(engine, NeverCalledProvider(), exercises=[])

    with pytest.raises(ExerciseNotFoundError):
        await service.evaluate("attempt_1")


@pytest.mark.asyncio
async def test_evaluate_sends_exercise_and_answer_in_the_request(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> EvaluatorResponse:
        captured.append(request)
        return _evaluator_response()

    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _capture)
    service, _ = _service(engine, provider)

    await service.evaluate("attempt_1")

    sent = captured[0]
    assert sent.role == "evaluator"
    assert sent.prompt_version == "evaluator.v1"
    assert sent.task["prompt"] == "Write a query using ROW_NUMBER()."
    assert sent.task["solution"] == "SELECT ROW_NUMBER() OVER (...) FROM t;"
    assert sent.task["answer"] == "SELECT ROW_NUMBER() OVER (ORDER BY id) FROM t;"
    assert sent.task["confidence"] == 72
