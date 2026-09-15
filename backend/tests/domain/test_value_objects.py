from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.entities import Concept, Evidence, Exercise, LearningGoal
from app.domain.enums import (
    ConceptStatus,
    EvidenceSourceType,
    ExerciseType,
    GoalStatus,
    TargetLevel,
)

NOW = datetime.now(UTC)


def _make_concept(**overrides: object) -> Concept:
    defaults = dict(
        id="concept_1",
        title="Window Functions",
        domain="sql",
        status=ConceptStatus.UNKNOWN,
        mastery=2.5,
        confidence=50,
        importance=3,
        retention=50,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return Concept(**defaults)  # type: ignore[arg-type]


def test_mastery_accepts_boundary_values() -> None:
    assert _make_concept(mastery=0).mastery == 0
    assert _make_concept(mastery=5).mastery == 5


@pytest.mark.parametrize("value", [-0.1, 5.1, -1, 6])
def test_mastery_rejects_out_of_range(value: float) -> None:
    with pytest.raises(ValidationError):
        _make_concept(mastery=value)


@pytest.mark.parametrize("value", [-1, 101])
def test_confidence_percent_rejects_out_of_range(value: float) -> None:
    with pytest.raises(ValidationError):
        _make_concept(confidence=value)


@pytest.mark.parametrize("value", [-1, 101])
def test_retention_percent_rejects_out_of_range(value: float) -> None:
    with pytest.raises(ValidationError):
        _make_concept(retention=value)


@pytest.mark.parametrize("value", [0, 6])
def test_importance_rejects_outside_one_to_five(value: int) -> None:
    with pytest.raises(ValidationError):
        _make_concept(importance=value)


def test_goal_priority_rejects_outside_one_to_five() -> None:
    with pytest.raises(ValidationError):
        LearningGoal(
            id="goal_1",
            title="Learn BigQuery",
            target_level=TargetLevel.PROFESSIONAL,
            status=GoalStatus.DRAFT,
            priority=6,
            created_at=NOW,
            updated_at=NOW,
        )


def test_exercise_difficulty_rejects_outside_one_to_five() -> None:
    with pytest.raises(ValidationError):
        Exercise(
            id="exercise_1",
            type=ExerciseType.SQL,
            difficulty=0,
            goal_id="goal_1",
            prompt="...",
            solution="...",
            created_at=NOW,
        )


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_evidence_normalized_scores_reject_outside_zero_to_one(value: float) -> None:
    with pytest.raises(ValidationError):
        Evidence(
            id="evidence_1",
            concept_id="concept_1",
            goal_id="goal_1",
            activity_id="activity_1",
            source_type=EvidenceSourceType.EXERCISE,
            difficulty=2,
            correctness=value,
            timestamp=NOW,
        )


def test_evidence_normalized_scores_accept_boundaries() -> None:
    evidence = Evidence(
        id="evidence_1",
        concept_id="concept_1",
        goal_id="goal_1",
        activity_id="activity_1",
        source_type=EvidenceSourceType.EXERCISE,
        difficulty=2,
        correctness=0,
        reasoning=1,
        timestamp=NOW,
    )
    assert evidence.correctness == 0
    assert evidence.reasoning == 1
