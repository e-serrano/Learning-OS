from sqlalchemy import Engine

from app.domain.entities import Activity
from app.domain.enums import ActivityStatus, ActivityType
from app.domain.ports import ActivityRepository
from app.persistence.repositories import SqlActivityRepository


def _accepts_port(port: ActivityRepository) -> ActivityRepository:
    return port


def _make_activity(seeded: dict, **overrides: object) -> Activity:  # type: ignore[type-arg]
    defaults: dict[str, object] = dict(
        id="activity_2",
        session_id=seeded["session_id"],
        type=ActivityType.EXERCISE,
        sequence=2,
        concept_ids=[seeded["concept_id"]],
        status=ActivityStatus.PENDING,
    )
    defaults.update(overrides)
    return Activity(**defaults)  # type: ignore[arg-type]


def test_satisfies_activity_repository_port(engine: Engine) -> None:
    _accepts_port(SqlActivityRepository(engine))


def test_add_then_get_roundtrips_including_concept_ids(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlActivityRepository(engine)
    activity = _make_activity(seeded)
    repo.add(activity)

    assert repo.get("activity_2") == activity


def test_get_missing_returns_none(engine: Engine) -> None:
    assert SqlActivityRepository(engine).get("missing") is None


def test_list_by_session_orders_by_sequence(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlActivityRepository(engine)
    repo.add(_make_activity(seeded, id="activity_3", sequence=3))
    repo.add(_make_activity(seeded, id="activity_2", sequence=2))

    ordered = [a.id for a in repo.list_by_session(seeded["session_id"])]
    assert ordered == ["activity_1", "activity_2", "activity_3"]


def test_list_by_session_excludes_other_sessions(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlActivityRepository(engine)

    assert [a.id for a in repo.list_by_session("other_session")] == []


def test_update_persists_status_change(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlActivityRepository(engine)
    activity = _make_activity(seeded)
    repo.add(activity)

    repo.update(activity.model_copy(update={"status": ActivityStatus.COMPLETED}))

    loaded = repo.get("activity_2")
    assert loaded is not None
    assert loaded.status == ActivityStatus.COMPLETED
