from datetime import datetime

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import Review
from app.persistence.models import ReviewModel
from app.persistence.repositories._util import dt_to_str, str_to_dt


def _to_model(review: Review) -> ReviewModel:
    return ReviewModel(
        id=review.id,
        goal_id=review.goal_id,
        concept_id=review.concept_id,
        scheduled_at=dt_to_str(review.scheduled_at),
        completed_at=dt_to_str(review.completed_at),
        interval_days=review.interval_days,
        stability=review.stability,
        difficulty=review.difficulty,
        status=review.status.value,
    )


def _to_entity(model: ReviewModel) -> Review:
    return Review(
        id=model.id,
        goal_id=model.goal_id,
        concept_id=model.concept_id,
        scheduled_at=str_to_dt(model.scheduled_at),  # type: ignore[arg-type]
        completed_at=str_to_dt(model.completed_at),
        interval_days=model.interval_days,
        stability=model.stability,
        difficulty=model.difficulty,
        status=model.status,  # type: ignore[arg-type]
    )


class SqlReviewRepository:
    """Implements app.domain.ports.ReviewRepository against reviews (T033)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, review: Review) -> None:
        with DbSession(self._engine) as db:
            db.add(_to_model(review))
            db.commit()

    def get(self, review_id: str) -> Review | None:
        with DbSession(self._engine) as db:
            model = db.get(ReviewModel, review_id)
            return _to_entity(model) if model is not None else None

    def list_due(self, before: datetime) -> list[Review]:
        with DbSession(self._engine) as db:
            stmt = select(ReviewModel).where(ReviewModel.scheduled_at <= dt_to_str(before))
            return [_to_entity(m) for m in db.scalars(stmt)]

    def list_by_concept(self, concept_id: str) -> list[Review]:
        with DbSession(self._engine) as db:
            stmt = select(ReviewModel).where(ReviewModel.concept_id == concept_id)
            return [_to_entity(m) for m in db.scalars(stmt)]

    def update(self, review: Review) -> None:
        with DbSession(self._engine) as db:
            db.merge(_to_model(review))
            db.commit()
