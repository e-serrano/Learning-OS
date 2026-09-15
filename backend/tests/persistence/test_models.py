from pathlib import Path

from sqlalchemy.orm import Session as DbSession

from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import (
    ActivityModel,
    AIRunModel,
    ConceptModel,
    ConceptRelationModel,
    EvaluationModel,
    EvidenceModel,
    ExerciseAttemptModel,
    ExerciseConceptModel,
    ExerciseModel,
    GoalConceptModel,
    GoalModel,
    MistakeModel,
    ReviewModel,
    SessionModel,
    SkillConceptModel,
    SkillModel,
    VaultFileModel,
)

EXPECTED_TABLES = {
    "goals",
    "concepts",
    "goal_concepts",
    "concept_relations",
    "skills",
    "skill_concepts",
    "sessions",
    "activities",
    "exercises",
    "exercise_concepts",
    "exercise_attempts",
    "evaluations",
    "evidence",
    "mistakes",
    "reviews",
    "ai_runs",
    "vault_files",
}


def test_all_database_schema_tables_are_registered_on_base_metadata() -> None:
    assert set(Base.metadata.tables.keys()) == EXPECTED_TABLES


def test_expected_indexes_are_present() -> None:
    index_names = {ix.name for table in Base.metadata.tables.values() for ix in table.indexes}
    assert index_names == {
        "idx_concepts_next_review",
        "idx_evidence_concept_time",
        "idx_evidence_goal_time",
        "idx_reviews_schedule",
        "idx_mistakes_concept",
        "idx_vault_files_hash",
    }


def test_evidence_table_has_three_foreign_keys() -> None:
    evidence_table = Base.metadata.tables["evidence"]
    fk_targets = {fk.column.table.name for fk in evidence_table.foreign_keys}
    assert fk_targets == {"goals", "concepts", "activities"}


def test_composite_primary_keys_match_schema() -> None:
    assert {c.name for c in Base.metadata.tables["goal_concepts"].primary_key.columns} == {
        "goal_id",
        "concept_id",
    }
    assert {c.name for c in Base.metadata.tables["concept_relations"].primary_key.columns} == {
        "source_id",
        "target_id",
        "relation",
    }


def test_model_classes_are_all_importable() -> None:
    """Guards against a model existing but not being registered in models/__init__.py."""
    model_classes = [
        AIRunModel,
        ActivityModel,
        ConceptModel,
        ConceptRelationModel,
        EvaluationModel,
        EvidenceModel,
        ExerciseAttemptModel,
        ExerciseConceptModel,
        ExerciseModel,
        GoalConceptModel,
        GoalModel,
        MistakeModel,
        ReviewModel,
        SessionModel,
        SkillConceptModel,
        SkillModel,
        VaultFileModel,
    ]
    assert len(model_classes) == len(EXPECTED_TABLES)
    assert {m.__tablename__ for m in model_classes} == EXPECTED_TABLES


def test_goal_model_roundtrips_through_real_sqlite(tmp_path: Path) -> None:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)

    with DbSession(engine) as db:
        db.add(
            GoalModel(
                id="goal_1",
                title="Learn BigQuery",
                target_level="professional",
                status="draft",
                priority=3,
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        db.commit()

    with DbSession(engine) as db:
        loaded = db.get(GoalModel, "goal_1")
        assert loaded is not None
        assert loaded.title == "Learn BigQuery"
