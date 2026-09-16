from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import Concept, ConceptRelation, Evidence, LearningGoal, Mistake
from app.domain.enums import (
    ConceptRelationType,
    ConceptStatus,
    EvidenceSourceType,
    GoalStatus,
    MistakeSeverity,
    MistakeType,
    TargetLevel,
)
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import ActivityModel, SessionModel
from app.persistence.repositories import (
    SqlConceptRelationRepository,
    SqlConceptRepository,
    SqlEvidenceRepository,
    SqlGoalRepository,
    SqlMistakeRepository,
)
from app.services.context_builder import ConceptNotFoundError, ContextBuilder, GoalNotFoundError

NOW = datetime.now(UTC)


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _builder(engine: Engine, **overrides: int) -> ContextBuilder:
    return ContextBuilder(
        goals=SqlGoalRepository(engine),
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        mistakes=SqlMistakeRepository(engine),
        **overrides,  # type: ignore[arg-type]
    )


def _seed_goal_and_concept(engine: Engine) -> None:
    SqlGoalRepository(engine).add(
        LearningGoal(
            id="goal_1",
            title="Learn SQL",
            target_level=TargetLevel.PROFESSIONAL,
            status=GoalStatus.ACTIVE,
            priority=3,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    SqlConceptRepository(engine).add(
        Concept(
            id="concept_1",
            title="Window Functions",
            domain="sql",
            status=ConceptStatus.LEARNING,
            mastery=1.5,
            confidence=40,
            importance=4,
            retention=60,
            created_at=NOW,
            updated_at=NOW,
        )
    )


def _seed_session_and_activity(engine: Engine) -> None:
    with DbSession(engine) as db:
        db.add(
            SessionModel(
                id="session_1",
                goal_id="goal_1",
                mode="guided",
                objective="Practice",
                status="planned",
                created_at=NOW.isoformat(),
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
                created_at=NOW.isoformat(),
            )
        )
        db.commit()


def test_build_raises_when_goal_not_found(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    SqlConceptRepository(engine).add(
        Concept(
            id="concept_1",
            title="X",
            domain="sql",
            status=ConceptStatus.UNKNOWN,
            mastery=0,
            confidence=0,
            importance=3,
            retention=0,
            created_at=NOW,
            updated_at=NOW,
        )
    )

    with pytest.raises(GoalNotFoundError):
        _builder(engine).build("missing_goal", "concept_1")


def test_build_raises_when_concept_not_found(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)

    with pytest.raises(ConceptNotFoundError):
        _builder(engine).build("goal_1", "missing_concept")


def test_build_leads_with_goal_then_concept(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)

    context = _builder(engine).build("goal_1", "concept_1")

    assert context[0] == {
        "kind": "goal",
        "id": "goal_1",
        "title": "Learn SQL",
        "target_level": "professional",
    }
    assert context[1]["kind"] == "concept"
    assert context[1]["id"] == "concept_1"
    assert context[1]["mastery"] == 1.5


def test_build_includes_prerequisite_concepts(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    SqlConceptRepository(engine).add(
        Concept(
            id="select_basics",
            title="SELECT basics",
            domain="sql",
            status=ConceptStatus.MASTERED,
            mastery=5,
            confidence=100,
            importance=3,
            retention=100,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    SqlConceptRelationRepository(engine).add(
        ConceptRelation(
            source_id="select_basics",
            target_id="concept_1",
            relation=ConceptRelationType.PREREQUISITE_OF,
        )
    )

    context = _builder(engine).build("goal_1", "concept_1")

    prerequisites = [item for item in context if item["kind"] == "prerequisite"]
    assert prerequisites == [
        {
            "kind": "prerequisite",
            "id": "select_basics",
            "title": "SELECT basics",
            "status": "mastered",
            "mastery": 5.0,
        }
    ]


def test_build_excludes_resolved_mistakes(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    mistakes = SqlMistakeRepository(engine)
    mistakes.add(
        Mistake(
            id="mistake_open",
            concept_id="concept_1",
            goal_id="goal_1",
            type=MistakeType.MISCONCEPTION,
            description="Confuses ROW_NUMBER and RANK",
            severity=MistakeSeverity.MEDIUM,
            occurrences=2,
            first_seen=NOW,
            last_seen=NOW,
        )
    )
    mistakes.add(
        Mistake(
            id="mistake_resolved",
            concept_id="concept_1",
            goal_id="goal_1",
            type=MistakeType.RECALL,
            description="Forgot PARTITION BY",
            severity=MistakeSeverity.LOW,
            occurrences=1,
            first_seen=NOW,
            last_seen=NOW,
            resolved_at=NOW,
        )
    )

    context = _builder(engine).build("goal_1", "concept_1")

    mistake_ids = {item["id"] for item in context if item["kind"] == "mistake"}
    assert mistake_ids == {"mistake_open"}


def test_build_orders_mistakes_most_recent_first_and_respects_cap(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    mistakes = SqlMistakeRepository(engine)
    for i in range(3):
        mistakes.add(
            Mistake(
                id=f"mistake_{i}",
                concept_id="concept_1",
                goal_id="goal_1",
                type=MistakeType.MISCONCEPTION,
                description=f"mistake {i}",
                severity=MistakeSeverity.LOW,
                occurrences=1,
                first_seen=NOW,
                last_seen=NOW + timedelta(hours=i),
            )
        )

    context = _builder(engine, max_mistakes=2).build("goal_1", "concept_1")

    mistake_ids = [item["id"] for item in context if item["kind"] == "mistake"]
    assert mistake_ids == ["mistake_2", "mistake_1"]


def test_build_orders_practice_most_recent_first_and_respects_cap(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    _seed_session_and_activity(engine)
    evidence = SqlEvidenceRepository(engine)
    for i in range(3):
        evidence.add(
            Evidence(
                id=f"evidence_{i}",
                concept_id="concept_1",
                goal_id="goal_1",
                session_id="session_1",
                activity_id="activity_1",
                source_type=EvidenceSourceType.EXERCISE,
                difficulty=3,
                correctness=0.8,
                timestamp=NOW + timedelta(hours=i),
            )
        )

    context = _builder(engine, max_recent_evidence=2).build("goal_1", "concept_1")

    practice_ids = [item["id"] for item in context if item["kind"] == "practice"]
    assert practice_ids == ["evidence_2", "evidence_1"]


def test_build_never_pulls_in_other_concepts_practice_or_mistakes(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concept(engine)
    SqlConceptRepository(engine).add(
        Concept(
            id="unrelated_concept",
            title="Unrelated",
            domain="sql",
            status=ConceptStatus.UNKNOWN,
            mastery=0,
            confidence=0,
            importance=3,
            retention=0,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    SqlMistakeRepository(engine).add(
        Mistake(
            id="mistake_unrelated",
            concept_id="unrelated_concept",
            goal_id="goal_1",
            type=MistakeType.MISCONCEPTION,
            description="unrelated",
            severity=MistakeSeverity.LOW,
            occurrences=1,
            first_seen=NOW,
            last_seen=NOW,
        )
    )

    context = _builder(engine).build("goal_1", "concept_1")

    assert all(item.get("id") != "mistake_unrelated" for item in context)
