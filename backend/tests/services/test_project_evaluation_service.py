from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import EvaluatorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Evidence, Project
from app.domain.enums import EvidenceSourceType, ProjectStatus
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.services.project_evaluation_service import ProjectEvaluationService
from app.services.project_submission_service import ProjectNotFoundError

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeProjectRepository:
    def __init__(self, projects: list[Project]) -> None:
        self._by_id = {p.id: p for p in projects}

    def get(self, project_id: str) -> Project | None:
        return self._by_id.get(project_id)

    def add(self, project: Project) -> None:
        self._by_id[project.id] = project

    def list_by_goal(self, goal_id: str) -> list[Project]:
        return [p for p in self._by_id.values() if p.goal_id == goal_id]

    def update(self, project: Project) -> None:
        self._by_id[project.id] = project


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


class NeverCalledProvider:
    async def generate(self, request: object, response_model: object) -> object:
        raise AssertionError("AI provider must not be called")


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _project(**overrides: object) -> Project:
    defaults: dict[str, object] = dict(
        id="project_1",
        goal_id="goal_1",
        title="Build a small ETL pipeline",
        objective="Build a pipeline that ranks top products per warehouse.",
        difficulty=4,
        status=ProjectStatus.ACTIVE,
        concept_ids=["window_functions"],
        success_criteria=["Uses at least one window function"],
    )
    defaults.update(overrides)
    return Project(**defaults)  # type: ignore[arg-type]


def _service(
    tmp_path: Path, provider: object, projects: list[Project] | None = None
) -> tuple[ProjectEvaluationService, FakeEvidenceRepository]:
    engine = _engine(tmp_path)
    evidence = FakeEvidenceRepository()
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    service = ProjectEvaluationService(
        FakeProjectRepository(projects if projects is not None else [_project()]),
        evidence,
        orchestrator,
        FakeClock(),
        FakeIdGenerator(),
    )
    return service, evidence


def _evaluator_response(**overrides: object) -> EvaluatorResponse:
    defaults: dict[str, object] = dict(
        correctness=0.9,
        reasoning=0.8,
        completeness=0.85,
        independence=0.7,
        transfer=0.75,
        feedback="Solid application of the concept to a new domain.",
        recommended_action="advance",
    )
    defaults.update(overrides)
    return EvaluatorResponse(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_evaluate_submission_creates_scored_evidence(tmp_path: Path) -> None:
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _evaluator_response())
    service, evidence = _service(tmp_path, provider)

    created = await service.evaluate_submission(
        "project_1", "task_1", "session_1", "https://github.com/x/y"
    )

    assert len(created) == 1
    record = created[0]
    assert record.source_type == EvidenceSourceType.PROJECT
    assert record.concept_id == "window_functions"
    assert record.independence == 0.7
    assert record.transfer == 0.75
    assert record.correctness == 0.9
    assert record.activity_id == "task_1"
    assert record.session_id == "session_1"
    assert evidence.added == created


@pytest.mark.asyncio
async def test_evaluate_submission_creates_one_row_per_concept(tmp_path: Path) -> None:
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _evaluator_response())
    service, evidence = _service(tmp_path, provider, projects=[_project(concept_ids=["a", "b"])])

    created = await service.evaluate_submission("project_1", "task_1", "session_1", "deliverable")

    assert {e.concept_id for e in created} == {"a", "b"}
    assert len(evidence.added) == 2


@pytest.mark.asyncio
async def test_evaluate_submission_raises_when_project_not_found_without_calling_ai(
    tmp_path: Path,
) -> None:
    service, evidence = _service(tmp_path, NeverCalledProvider(), projects=[])

    with pytest.raises(ProjectNotFoundError):
        await service.evaluate_submission("missing_project", "task_1", "session_1", "x")

    assert evidence.added == []


@pytest.mark.asyncio
async def test_evaluate_submission_sends_objective_criteria_and_deliverable(
    tmp_path: Path,
) -> None:
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> EvaluatorResponse:
        captured.append(request)
        return _evaluator_response()

    provider = MockProvider()
    provider.set_response(EvaluatorResponse, _capture)
    service, _ = _service(tmp_path, provider)

    await service.evaluate_submission("project_1", "task_1", "session_1", "https://github.com/x/y")

    sent = captured[0]
    assert sent.role == "evaluator"
    assert sent.task["prompt"] == "Build a pipeline that ranks top products per warehouse."
    assert sent.task["success_criteria"] == ["Uses at least one window function"]
    assert sent.task["answer"] == "https://github.com/x/y"
