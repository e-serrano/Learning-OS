from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.entities import (
    Activity,
    Assessment,
    Concept,
    ConceptRelation,
    Evaluation,
    Evidence,
    Exercise,
    ExerciseAttempt,
    LearningGoal,
    Mistake,
    Project,
    Review,
    Roadmap,
    Session,
    Skill,
)
from app.domain.enums import (
    ActivityStatus,
    ActivityType,
    AssessmentType,
    ConceptRelationType,
    ConceptStatus,
    EvidenceSourceType,
    ExerciseType,
    GoalStatus,
    MistakeSeverity,
    MistakeType,
    ProjectStatus,
    ReviewStatus,
    RoadmapStatus,
    SessionMode,
    SessionStatus,
    TargetLevel,
)

NOW = datetime.now(UTC)


def test_learning_goal_requires_title_and_target_level() -> None:
    goal = LearningGoal(
        id="goal_1",
        title="Learn BigQuery",
        target_level=TargetLevel.PROFESSIONAL,
        status=GoalStatus.DRAFT,
        priority=3,
        created_at=NOW,
        updated_at=NOW,
    )
    assert goal.description is None
    assert goal.status == GoalStatus.DRAFT


def test_concept_defaults() -> None:
    concept = Concept(
        id="concept_1",
        title="Window Functions",
        domain="sql",
        status=ConceptStatus.UNKNOWN,
        mastery=0,
        confidence=0,
        importance=3,
        retention=0,
        created_at=NOW,
        updated_at=NOW,
    )
    assert concept.last_practiced is None
    assert concept.obsidian_path is None


def test_concept_relation() -> None:
    relation = ConceptRelation(
        source_id="concept_1", target_id="concept_2", relation=ConceptRelationType.PREREQUISITE_OF
    )
    assert relation.weight is None


def test_skill_defaults_concept_ids_to_empty_list() -> None:
    skill = Skill(id="skill_1", title="Write window functions", description="...", mastery=0)
    assert skill.concept_ids == []


def test_evidence_is_immutable() -> None:
    evidence = Evidence(
        id="evidence_1",
        concept_id="concept_1",
        goal_id="goal_1",
        activity_id="activity_1",
        source_type=EvidenceSourceType.EXERCISE,
        difficulty=2,
        timestamp=NOW,
    )
    with pytest.raises(ValidationError):
        evidence.correctness = 0.9  # type: ignore[misc]


def test_evidence_metadata_defaults_to_empty_dict() -> None:
    evidence = Evidence(
        id="evidence_1",
        concept_id="concept_1",
        goal_id="goal_1",
        activity_id="activity_1",
        source_type=EvidenceSourceType.EXERCISE,
        difficulty=2,
        timestamp=NOW,
    )
    assert evidence.metadata == {}
    assert evidence.skill_ids == []


def test_exercise_defaults() -> None:
    exercise = Exercise(
        id="exercise_1",
        type=ExerciseType.SQL,
        difficulty=3,
        goal_id="goal_1",
        prompt="Write a query...",
        solution="SELECT ...",
        created_at=NOW,
    )
    assert exercise.concept_ids == []
    assert exercise.transfer_variant is None


def test_exercise_attempt_is_immutable() -> None:
    attempt = ExerciseAttempt(
        id="attempt_1",
        exercise_id="exercise_1",
        session_id="session_1",
        answer="SELECT 1",
        confidence=70,
        submitted_at=NOW,
    )
    with pytest.raises(ValidationError):
        attempt.answer = "changed"  # type: ignore[misc]


def test_evaluation_is_immutable() -> None:
    evaluation = Evaluation(
        id="evaluation_1",
        attempt_id="attempt_1",
        correctness=0.8,
        reasoning=0.7,
        completeness=0.9,
        independence=0.6,
        transfer=0.5,
        feedback="Good job",
        recommended_action="practice_more",
        provider="mock",
        model="mock-1",
        prompt_version="evaluator.v1",
        created_at=NOW,
    )
    with pytest.raises(ValidationError):
        evaluation.feedback = "changed"  # type: ignore[misc]
    assert evaluation.misconceptions == []


def test_mistake_defaults() -> None:
    mistake = Mistake(
        id="mistake_1",
        concept_id="concept_1",
        goal_id="goal_1",
        type=MistakeType.MISCONCEPTION,
        description="Confuses ROW_NUMBER and RANK",
        severity=MistakeSeverity.MEDIUM,
        occurrences=1,
        first_seen=NOW,
        last_seen=NOW,
    )
    assert mistake.resolved_at is None


def test_review_defaults() -> None:
    review = Review(
        id="review_1",
        concept_id="concept_1",
        goal_id="goal_1",
        scheduled_at=NOW,
        interval_days=3.0,
        status=ReviewStatus.SCHEDULED,
    )
    assert review.completed_at is None
    assert review.stability is None


def test_session_and_activity_defaults() -> None:
    session = Session(
        id="session_1",
        goal_id="goal_1",
        mode=SessionMode.GUIDED,
        objective="Practice window functions",
        status=SessionStatus.PLANNED,
    )
    assert session.started_at is None

    activity = Activity(
        id="activity_1",
        session_id="session_1",
        type=ActivityType.EXERCISE,
        sequence=1,
        status=ActivityStatus.PENDING,
    )
    assert activity.concept_ids == []


def test_project_defaults() -> None:
    project = Project(
        id="project_1",
        goal_id="goal_1",
        title="Build a dashboard",
        objective="Apply window functions in a real report",
        difficulty=3,
        status=ProjectStatus.PROPOSED,
    )
    assert project.success_criteria == []
    assert project.artifact_path is None


def test_assessment_defaults() -> None:
    assessment = Assessment(
        id="assessment_1", goal_id="goal_1", type=AssessmentType.DIAGNOSTIC, difficulty=2
    )
    assert assessment.target_concept_ids == []


def test_roadmap() -> None:
    roadmap = Roadmap(id="roadmap_1", goal_id="goal_1", version=1, status=RoadmapStatus.ACTIVE)
    assert roadmap.version == 1
