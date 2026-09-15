
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import (
    ActivityModel,
    ConceptModel,
    EvidenceModel,
    GoalModel,
    SessionModel,
)

NOW = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def engine(tmp_path):  # type: ignore[no-untyped-def]
    eng = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(eng)
    return eng


def _goal(id_: str = "goal_1") -> GoalModel:
    return GoalModel(
        id=id_,
        title="Learn BigQuery",
        target_level="professional",
        status="draft",
        priority=3,
        created_at=NOW,
        updated_at=NOW,
    )


def test_explicit_rollback_discards_uncommitted_insert(engine) -> None:  # type: ignore[no-untyped-def]
    with DbSession(engine) as db:
        db.add(_goal())
        db.flush()  # row visible within the transaction
        db.rollback()

    with DbSession(engine) as db:
        assert db.get(GoalModel, "goal_1") is None


def test_exception_before_commit_leaves_no_partial_state(engine) -> None:  # type: ignore[no-untyped-def]
    """Session context manager rolls back automatically on exception."""
    with pytest.raises(IntegrityError), DbSession(engine) as db:
        db.add(_goal())
        db.flush()
        db.add(_goal())  # duplicate PK -> IntegrityError
        db.flush()

    with DbSession(engine) as db:
        assert db.get(GoalModel, "goal_1") is None


def test_committed_data_survives_a_later_session(engine) -> None:  # type: ignore[no-untyped-def]
    with DbSession(engine) as db:
        db.add(_goal())
        db.commit()

    with DbSession(engine) as db:
        assert db.get(GoalModel, "goal_1") is not None


def test_partial_multi_table_transaction_rolls_back_together(engine) -> None:  # type: ignore[no-untyped-def]
    """A goal + concept added in one transaction that later fails: neither persists."""
    with pytest.raises(IntegrityError), DbSession(engine) as db:
        db.add(_goal())
        db.flush()
        db.add(
            ConceptModel(
                id="concept_1",
                title="Window Functions",
                domain="sql",
                status="unknown",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        db.flush()
        # violates FK: no such goal
        db.add(
            EvidenceModel(
                id="evidence_1",
                goal_id="does-not-exist",
                concept_id="concept_1",
                activity_id="does-not-exist-either",
                source_type="exercise",
                difficulty=1,
                timestamp=NOW,
                metadata_json="{}",
            )
        )
        db.flush()

    with DbSession(engine) as db:
        assert db.get(GoalModel, "goal_1") is None
        assert db.get(ConceptModel, "concept_1") is None


def test_evidence_append_only_survives_across_many_sequential_writes(engine) -> None:  # type: ignore[no-untyped-def]
    """Each evidence write is its own committed transaction; nothing is ever overwritten."""
    with DbSession(engine) as db:
        db.add(_goal())
        db.flush()
        db.add(
            ConceptModel(
                id="concept_1",
                title="Window Functions",
                domain="sql",
                status="unknown",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        db.flush()
        db.add(
            SessionModel(
                id="session_1",
                goal_id="goal_1",
                mode="guided",
                objective="Practice",
                status="planned",
                created_at=NOW,
            )
        )
        db.flush()
        db.add(
            ActivityModel(
                id="activity_1",
                session_id="session_1",
                type="exercise",
                sequence=1,
                status="pending",
                payload_json="{}",
                created_at=NOW,
            )
        )
        db.commit()

    for i in range(5):
        with DbSession(engine) as db:
            db.add(
                EvidenceModel(
                    id=f"evidence_{i}",
                    goal_id="goal_1",
                    concept_id="concept_1",
                    activity_id="activity_1",
                    source_type="exercise",
                    difficulty=1,
                    timestamp=NOW,
                    metadata_json="{}",
                )
            )
            db.commit()

    with DbSession(engine) as db:
        rows = list(db.scalars(select(EvidenceModel).where(EvidenceModel.goal_id == "goal_1")))
        assert len(rows) == 5
        assert len({r.id for r in rows}) == 5
