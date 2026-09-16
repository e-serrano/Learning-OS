from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine

from app.domain.entities import Review
from app.domain.enums import ReviewStatus
from app.domain.ports import ReviewRepository
from app.persistence.repositories import SqlReviewRepository

NOW = datetime.now(UTC)


def _accepts_port(port: ReviewRepository) -> ReviewRepository:
    return port


def _make_review(seeded: dict, **overrides: object) -> Review:  # type: ignore[type-arg]
    defaults: dict[str, object] = dict(
        id="review_1",
        concept_id=seeded["concept_id"],
        goal_id=seeded["goal_id"],
        scheduled_at=NOW,
        interval_days=3.0,
        status=ReviewStatus.SCHEDULED,
    )
    defaults.update(overrides)
    return Review(**defaults)  # type: ignore[arg-type]


def test_satisfies_review_repository_port(engine: Engine) -> None:
    _accepts_port(SqlReviewRepository(engine))


def test_add_then_get_roundtrips(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlReviewRepository(engine)
    review = _make_review(seeded)
    repo.add(review)

    assert repo.get("review_1") == review


def test_update_persists_changes(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlReviewRepository(engine)
    repo.add(_make_review(seeded))
    repo.update(_make_review(seeded, status=ReviewStatus.COMPLETED, completed_at=NOW))

    loaded = repo.get("review_1")
    assert loaded is not None
    assert loaded.status == ReviewStatus.COMPLETED
    assert loaded.completed_at == NOW


def test_list_due_filters_by_scheduled_at(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlReviewRepository(engine)
    repo.add(_make_review(seeded, id="due", scheduled_at=NOW - timedelta(days=1)))
    repo.add(_make_review(seeded, id="not_due", scheduled_at=NOW + timedelta(days=10)))

    due = {r.id for r in repo.list_due(NOW)}
    assert due == {"due"}


def test_list_by_concept_returns_only_that_concepts_reviews(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlReviewRepository(engine)
    repo.add(_make_review(seeded, id="review_1"))

    assert [r.id for r in repo.list_by_concept(seeded["concept_id"])] == ["review_1"]
    assert repo.list_by_concept("some_other_concept") == []
