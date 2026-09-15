from sqlalchemy import Engine

from app.domain.entities import Session
from app.domain.enums import SessionMode, SessionStatus
from app.domain.ports import SessionRepository
from app.persistence.repositories import SqlSessionRepository


def _accepts_port(port: SessionRepository) -> SessionRepository:
    return port


def _make_session(seeded: dict, **overrides: object) -> Session:  # type: ignore[type-arg]
    defaults: dict[str, object] = dict(
        id="session_new",
        goal_id=seeded["goal_id"],
        mode=SessionMode.GUIDED,
        objective="Practice window functions",
        status=SessionStatus.PLANNED,
    )
    defaults.update(overrides)
    return Session(**defaults)  # type: ignore[arg-type]


def test_satisfies_session_repository_port(engine: Engine) -> None:
    _accepts_port(SqlSessionRepository(engine))


def test_add_then_get_roundtrips(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlSessionRepository(engine)
    session = _make_session(seeded)
    repo.add(session)

    assert repo.get("session_new") == session


def test_update_preserves_created_at_and_persists_changes(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlSessionRepository(engine)
    repo.add(_make_session(seeded))
    repo.update(_make_session(seeded, status=SessionStatus.COMPLETED))

    loaded = repo.get("session_new")
    assert loaded is not None
    assert loaded.status == SessionStatus.COMPLETED


def test_get_missing_returns_none(engine: Engine) -> None:
    repo = SqlSessionRepository(engine)
    assert repo.get("does-not-exist") is None
