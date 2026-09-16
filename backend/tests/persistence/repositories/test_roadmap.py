from sqlalchemy import Engine

from app.domain.entities import Roadmap
from app.domain.enums import RoadmapStatus
from app.domain.ports import RoadmapRepository
from app.persistence.repositories import SqlRoadmapRepository


def _accepts_port(port: RoadmapRepository) -> RoadmapRepository:
    return port


def _make_roadmap(**overrides: object) -> Roadmap:
    defaults: dict[str, object] = dict(
        id="roadmap_1",
        goal_id="goal_1",
        version=1,
        status=RoadmapStatus.ACTIVE,
    )
    defaults.update(overrides)
    return Roadmap(**defaults)  # type: ignore[arg-type]


def test_satisfies_roadmap_repository_port(engine: Engine) -> None:
    _accepts_port(SqlRoadmapRepository(engine))


def test_add_then_get_active_for_goal_roundtrips(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlRoadmapRepository(engine)
    roadmap = _make_roadmap(goal_id=seeded["goal_id"])
    repo.add(roadmap)

    assert repo.get_active_for_goal(seeded["goal_id"]) == roadmap


def test_get_active_for_goal_ignores_superseded_roadmaps(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlRoadmapRepository(engine)
    repo.add(
        _make_roadmap(
            id="roadmap_old", goal_id=seeded["goal_id"], version=1, status=RoadmapStatus.SUPERSEDED
        )
    )

    assert repo.get_active_for_goal(seeded["goal_id"]) is None


def test_update_persists_status_change(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlRoadmapRepository(engine)
    roadmap = _make_roadmap(goal_id=seeded["goal_id"])
    repo.add(roadmap)

    repo.update(roadmap.model_copy(update={"status": RoadmapStatus.SUPERSEDED}))

    assert repo.get_active_for_goal(seeded["goal_id"]) is None


def test_get_active_for_goal_excludes_other_goals(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlRoadmapRepository(engine)
    repo.add(_make_roadmap(goal_id=seeded["goal_id"]))

    assert repo.get_active_for_goal("some_other_goal") is None
