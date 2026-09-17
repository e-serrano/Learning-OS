from sqlalchemy import Engine

from app.domain.entities import Project
from app.domain.enums import ProjectStatus
from app.domain.ports import ProjectRepository
from app.persistence.repositories import SqlProjectRepository


def _accepts_port(port: ProjectRepository) -> ProjectRepository:
    return port


def _make_project(seeded: dict, **overrides: object) -> Project:  # type: ignore[type-arg]
    defaults: dict[str, object] = dict(
        id="project_1",
        goal_id=seeded["goal_id"],
        title="Build a small ETL pipeline",
        objective="Practice window functions on a real dataset",
        difficulty=3,
        status=ProjectStatus.PROPOSED,
        concept_ids=[seeded["concept_id"]],
        success_criteria=["Uses at least one window function", "Handles duplicate rows"],
    )
    defaults.update(overrides)
    return Project(**defaults)  # type: ignore[arg-type]


def test_satisfies_project_repository_port(engine: Engine) -> None:
    _accepts_port(SqlProjectRepository(engine))


def test_add_then_get_roundtrips(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlProjectRepository(engine)
    project = _make_project(seeded)
    repo.add(project)

    assert repo.get("project_1") == project


def test_concept_ids_come_from_join_table(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlProjectRepository(engine)
    repo.add(_make_project(seeded, concept_ids=[seeded["concept_id"]]))

    loaded = repo.get("project_1")
    assert loaded is not None
    assert loaded.concept_ids == [seeded["concept_id"]]


def test_list_by_goal_returns_only_that_goals_projects(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlProjectRepository(engine)
    repo.add(_make_project(seeded, id="project_1"))

    assert [p.id for p in repo.list_by_goal(seeded["goal_id"])] == ["project_1"]
    assert repo.list_by_goal("some_other_goal") == []


def test_update_persists_status_change(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlProjectRepository(engine)
    project = _make_project(seeded)
    repo.add(project)

    repo.update(project.model_copy(update={"status": ProjectStatus.ACTIVE}))

    loaded = repo.get("project_1")
    assert loaded is not None
    assert loaded.status == ProjectStatus.ACTIVE


def test_update_replaces_concept_links(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlProjectRepository(engine)
    repo.add(_make_project(seeded, concept_ids=[seeded["concept_id"]]))

    repo.update(_make_project(seeded, concept_ids=[]))

    loaded = repo.get("project_1")
    assert loaded is not None
    assert loaded.concept_ids == []


def test_get_missing_returns_none(engine: Engine) -> None:
    assert SqlProjectRepository(engine).get("missing") is None
