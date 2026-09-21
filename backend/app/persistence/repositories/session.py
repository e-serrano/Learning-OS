from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import Session
from app.persistence.models import SessionModel
from app.persistence.repositories._util import dt_to_str, now_iso, str_to_dt


def _to_model(session: Session, created_at: str) -> SessionModel:
    return SessionModel(
        id=session.id,
        goal_id=session.goal_id,
        mode=session.mode.value,
        objective=session.objective,
        status=session.status.value,
        started_at=dt_to_str(session.started_at),
        ended_at=dt_to_str(session.ended_at),
        created_at=created_at,
    )


def _to_entity(model: SessionModel) -> Session:
    return Session(
        id=model.id,
        goal_id=model.goal_id,
        mode=model.mode,  # type: ignore[arg-type]
        objective=model.objective,
        status=model.status,  # type: ignore[arg-type]
        started_at=str_to_dt(model.started_at),
        ended_at=str_to_dt(model.ended_at),
    )


class SqlSessionRepository:
    """Implements app.domain.ports.SessionRepository against sessions (T033).

    `created_at` is a DB-only bookkeeping column not present on the Session
    domain entity -- this repository manages it transparently.

    `list_by_goal` was added in T107 -- nothing before the progress
    summary route needed to list a goal's sessions at all.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, session: Session) -> None:
        with DbSession(self._engine) as db:
            db.add(_to_model(session, created_at=now_iso()))
            db.commit()

    def get(self, session_id: str) -> Session | None:
        with DbSession(self._engine) as db:
            model = db.get(SessionModel, session_id)
            return _to_entity(model) if model is not None else None

    def list_by_goal(self, goal_id: str) -> list[Session]:
        with DbSession(self._engine) as db:
            stmt = select(SessionModel).where(SessionModel.goal_id == goal_id)
            return [_to_entity(m) for m in db.scalars(stmt)]

    def update(self, session: Session) -> None:
        with DbSession(self._engine) as db:
            existing = db.get(SessionModel, session.id)
            created_at = existing.created_at if existing is not None else now_iso()
            db.merge(_to_model(session, created_at=created_at))
            db.commit()
