from datetime import UTC, datetime

import pytest

from app.domain.entities import Activity, Project, Session
from app.domain.enums import (
    ActivityStatus,
    ActivityType,
    ProjectStatus,
    SessionMode,
    SessionStatus,
)
from app.services.project_task_service import ProjectNotFoundError, ProjectTaskService

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


class FakeSessionRepository:
    def __init__(self) -> None:
        self.added: list[Session] = []

    def add(self, session: Session) -> None:
        self.added.append(session)

    def get(self, session_id: str) -> Session | None:
        return next((s for s in self.added if s.id == session_id), None)

    def update(self, session: Session) -> None:
        raise NotImplementedError


class FakeActivityRepository:
    def __init__(self) -> None:
        self.added: list[Activity] = []

    def add(self, activity: Activity) -> None:
        self.added.append(activity)

    def get(self, activity_id: str) -> Activity | None:
        return next((a for a in self.added if a.id == activity_id), None)

    def list_by_session(self, session_id: str) -> list[Activity]:
        return [a for a in self.added if a.session_id == session_id]

    def update(self, activity: Activity) -> None:
        raise NotImplementedError


class FakeClock:
    def now(self) -> datetime:
        return NOW


class FakeIdGenerator:
    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    def new_id(self, prefix: str) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}_{self._counters[prefix]}"


def _project(**overrides: object) -> Project:
    defaults: dict[str, object] = dict(
        id="project_1",
        goal_id="goal_1",
        title="Build a small ETL pipeline",
        objective="Practice window functions on a real dataset",
        difficulty=3,
        status=ProjectStatus.PROPOSED,
        concept_ids=["window_functions"],
        success_criteria=["Uses at least one window function", "Handles duplicate rows"],
    )
    defaults.update(overrides)
    return Project(**defaults)  # type: ignore[arg-type]


def _service(
    projects: list[Project] | None = None,
) -> tuple[
    ProjectTaskService, FakeProjectRepository, FakeSessionRepository, FakeActivityRepository
]:
    project_repo = FakeProjectRepository(projects if projects is not None else [_project()])
    session_repo = FakeSessionRepository()
    activity_repo = FakeActivityRepository()
    service = ProjectTaskService(
        project_repo, session_repo, activity_repo, FakeClock(), FakeIdGenerator()
    )
    return service, project_repo, session_repo, activity_repo


def test_create_tasks_creates_a_project_session() -> None:
    service, _, sessions, _ = _service()

    result = service.create_tasks("project_1")

    assert result.session.mode == SessionMode.PROJECT
    assert result.session.status == SessionStatus.ACTIVE
    assert result.session.goal_id == "goal_1"
    assert sessions.added == [result.session]


def test_create_tasks_creates_one_activity_per_success_criterion() -> None:
    service, _, _, activities = _service()

    result = service.create_tasks("project_1")

    assert len(result.tasks) == 2
    assert [t.sequence for t in result.tasks] == [1, 2]
    assert all(t.type == ActivityType.PROJECT_TASK for t in result.tasks)
    assert all(t.status == ActivityStatus.PENDING for t in result.tasks)
    assert all(t.session_id == result.session.id for t in result.tasks)
    assert activities.added == result.tasks


def test_create_tasks_propagates_project_concept_ids_to_each_task() -> None:
    service, _, _, _ = _service(projects=[_project(concept_ids=["a", "b"])])

    result = service.create_tasks("project_1")

    assert all(t.concept_ids == ["a", "b"] for t in result.tasks)


def test_create_tasks_activates_a_proposed_project() -> None:
    service, projects, _, _ = _service(projects=[_project(status=ProjectStatus.PROPOSED)])

    service.create_tasks("project_1")

    assert projects.get("project_1").status == ProjectStatus.ACTIVE  # type: ignore[union-attr]


def test_create_tasks_leaves_an_already_active_project_active() -> None:
    service, projects, _, _ = _service(projects=[_project(status=ProjectStatus.ACTIVE)])

    service.create_tasks("project_1")

    assert projects.get("project_1").status == ProjectStatus.ACTIVE  # type: ignore[union-attr]


def test_create_tasks_with_no_success_criteria_creates_an_empty_task_list() -> None:
    service, _, _, _ = _service(projects=[_project(success_criteria=[])])

    result = service.create_tasks("project_1")

    assert result.tasks == []
    assert result.session is not None


def test_create_tasks_raises_when_project_not_found() -> None:
    service, _, sessions, activities = _service(projects=[])

    with pytest.raises(ProjectNotFoundError):
        service.create_tasks("missing_project")

    assert sessions.added == []
    assert activities.added == []
