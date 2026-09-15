from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import ActivityModel, ConceptModel, GoalModel, SessionModel


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    eng = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def seeded(engine: Engine) -> dict[str, str]:
    """Minimal goal+concept+session+activity so FK-constrained inserts succeed.

    Flushed sequentially (not one bulk add+commit): unrelated mapped classes
    with plain FK columns (no relationship()) aren't topologically sorted by
    SQLAlchemy's flush, so a single commit can emit them in add() order and
    trip SQLite's immediate FK checks.
    """
    now = "2026-01-01T00:00:00+00:00"
    with DbSession(engine) as db:
        db.add(
            GoalModel(
                id="goal_1",
                title="Learn BigQuery",
                target_level="professional",
                status="draft",
                priority=3,
                created_at=now,
                updated_at=now,
            )
        )
        db.flush()
        db.add(
            ConceptModel(
                id="concept_1",
                title="Window Functions",
                domain="sql",
                status="unknown",
                created_at=now,
                updated_at=now,
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
                created_at=now,
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
                created_at=now,
            )
        )
        db.commit()
    return {
        "goal_id": "goal_1",
        "concept_id": "concept_1",
        "session_id": "session_1",
        "activity_id": "activity_1",
    }
