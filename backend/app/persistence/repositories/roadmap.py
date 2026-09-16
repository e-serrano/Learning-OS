from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import Roadmap
from app.domain.enums import RoadmapStatus
from app.persistence.models import RoadmapModel


def _to_model(roadmap: Roadmap) -> RoadmapModel:
    return RoadmapModel(
        id=roadmap.id,
        goal_id=roadmap.goal_id,
        version=roadmap.version,
        status=roadmap.status.value,
    )


def _to_entity(model: RoadmapModel) -> Roadmap:
    return Roadmap(
        id=model.id,
        goal_id=model.goal_id,
        version=model.version,
        status=model.status,  # type: ignore[arg-type]
    )


class SqlRoadmapRepository:
    """Implements app.domain.ports.RoadmapRepository against roadmaps
    (T068 gap fix -- see docs/DATABASE_SCHEMA.md)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, roadmap: Roadmap) -> None:
        with DbSession(self._engine) as db:
            db.add(_to_model(roadmap))
            db.commit()

    def get_active_for_goal(self, goal_id: str) -> Roadmap | None:
        with DbSession(self._engine) as db:
            stmt = select(RoadmapModel).where(
                RoadmapModel.goal_id == goal_id,
                RoadmapModel.status == RoadmapStatus.ACTIVE.value,
            )
            model = db.scalars(stmt).first()
            return _to_entity(model) if model is not None else None

    def update(self, roadmap: Roadmap) -> None:
        with DbSession(self._engine) as db:
            db.merge(_to_model(roadmap))
            db.commit()
