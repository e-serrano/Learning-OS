from datetime import UTC, datetime

import pytest

from app.domain.entities import Activity, Evidence, Project
from app.domain.enums import ActivityStatus, ActivityType, EvidenceSourceType, ProjectStatus
from app.services.project_submission_service import (
    NotAProjectTaskError,
    ProjectNotFoundError,
    ProjectSubmissionService,
    TaskNotFoundError,
)

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


class FakeActivityRepository:
    def __init__(self, activities: list[Activity]) -> None:
        self._by_id = {a.id: a for a in activities}

    def get(self, activity_id: str) -> Activity | None:
        return self._by_id.get(activity_id)

    def add(self, activity: Activity) -> None:
        self._by_id[activity.id] = activity

    def list_by_session(self, session_id: str) -> list[Activity]:
        return [a for a in self._by_id.values() if a.session_id == session_id]

    def update(self, activity: Activity) -> None:
        self._by_id[activity.id] = activity


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


def _project(**overrides: object) -> Project:
    defaults: dict[str, object] = dict(
        id="project_1",
        goal_id="goal_1",
        title="Build a small ETL pipeline",
        objective="Practice window functions on a real dataset",
        difficulty=4,
        status=ProjectStatus.ACTIVE,
        concept_ids=["window_functions"],
        success_criteria=["Uses at least one window function"],
    )
    defaults.update(overrides)
    return Project(**defaults)  # type: ignore[arg-type]


def _task(**overrides: object) -> Activity:
    defaults: dict[str, object] = dict(
        id="task_1",
        session_id="session_1",
        type=ActivityType.PROJECT_TASK,
        sequence=1,
        concept_ids=["window_functions"],
        status=ActivityStatus.PENDING,
    )
    defaults.update(overrides)
    return Activity(**defaults)  # type: ignore[arg-type]


def _service(
    projects: list[Project] | None = None, tasks: list[Activity] | None = None
) -> tuple[ProjectSubmissionService, FakeActivityRepository, FakeEvidenceRepository]:
    activity_repo = FakeActivityRepository(tasks if tasks is not None else [_task()])
    evidence_repo = FakeEvidenceRepository()
    service = ProjectSubmissionService(
        FakeProjectRepository(projects if projects is not None else [_project()]),
        activity_repo,
        evidence_repo,
        FakeClock(),
        FakeIdGenerator(),
    )
    return service, activity_repo, evidence_repo


def test_submit_task_marks_the_task_completed() -> None:
    service, activities, _ = _service()

    result = service.submit_task("project_1", "task_1", deliverable="https://github.com/x/y")

    assert result.task.status == ActivityStatus.COMPLETED
    assert activities.get("task_1").status == ActivityStatus.COMPLETED  # type: ignore[union-attr]


def test_submit_task_creates_unscored_evidence_per_concept() -> None:
    service, _, evidence = _service()

    result = service.submit_task("project_1", "task_1", deliverable="https://github.com/x/y")

    assert len(result.evidence) == 1
    record = result.evidence[0]
    assert record.source_type == EvidenceSourceType.PROJECT
    assert record.concept_id == "window_functions"
    assert record.difficulty == 4
    assert record.correctness is None
    assert record.transfer is None
    assert record.independence is None
    assert record.metadata == {
        "deliverable": "https://github.com/x/y",
        "project_id": "project_1",
        "task_id": "task_1",
    }
    assert evidence.added == result.evidence


def test_submit_task_creates_one_evidence_row_per_concept() -> None:
    service, _, evidence = _service(
        projects=[_project(concept_ids=["a", "b"])],
        tasks=[_task(concept_ids=["a", "b"])],
    )

    result = service.submit_task("project_1", "task_1", deliverable="artifact")

    assert {e.concept_id for e in result.evidence} == {"a", "b"}
    assert len(evidence.added) == 2


def test_submit_task_raises_when_project_not_found() -> None:
    service, _, evidence = _service(projects=[])

    with pytest.raises(ProjectNotFoundError):
        service.submit_task("missing_project", "task_1", deliverable="x")

    assert evidence.added == []


def test_submit_task_raises_when_task_not_found() -> None:
    service, _, evidence = _service(tasks=[])

    with pytest.raises(TaskNotFoundError):
        service.submit_task("project_1", "missing_task", deliverable="x")

    assert evidence.added == []


def test_submit_task_raises_when_activity_is_not_a_project_task() -> None:
    service, _, evidence = _service(tasks=[_task(type=ActivityType.EXERCISE)])

    with pytest.raises(NotAProjectTaskError):
        service.submit_task("project_1", "task_1", deliverable="x")

    assert evidence.added == []
