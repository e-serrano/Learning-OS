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
    ProposalOperation,
    ReviewStatus,
    RoadmapStatus,
    SessionMode,
    SessionStatus,
    TargetLevel,
)


def test_target_level_matches_spec() -> None:
    assert {e.value for e in TargetLevel} == {
        "beginner",
        "intermediate",
        "advanced",
        "professional",
    }


def test_goal_status_matches_spec() -> None:
    assert {e.value for e in GoalStatus} == {
        "draft",
        "active",
        "paused",
        "completed",
        "archived",
    }


def test_concept_status_matches_spec() -> None:
    assert {e.value for e in ConceptStatus} == {
        "unknown",
        "learning",
        "weak",
        "developing",
        "usable",
        "strong",
        "mastered",
        "needs_review",
        "deprecated",
    }


def test_concept_relation_type_matches_spec() -> None:
    assert {e.value for e in ConceptRelationType} == {
        "PREREQUISITE_OF",
        "RELATED_TO",
        "PART_OF",
        "CONTRASTS_WITH",
        "APPLIED_BY",
    }


def test_evidence_source_type_matches_spec() -> None:
    assert {e.value for e in EvidenceSourceType} == {
        "exercise",
        "assessment",
        "teach_back",
        "project",
        "review",
        "self_report",
    }


def test_exercise_type_matches_spec() -> None:
    assert {e.value for e in ExerciseType} == {
        "mcq",
        "short_answer",
        "teach_back",
        "coding",
        "sql",
        "debugging",
        "design",
        "decision",
        "scenario",
        "comparison",
        "prediction",
    }


def test_mistake_type_matches_spec() -> None:
    assert {e.value for e in MistakeType} == {
        "misconception",
        "procedure",
        "recall",
        "reasoning",
        "attention",
        "calibration",
    }


def test_mistake_severity_matches_spec() -> None:
    assert {e.value for e in MistakeSeverity} == {"low", "medium", "high"}


def test_review_status_matches_spec() -> None:
    assert {e.value for e in ReviewStatus} == {
        "scheduled",
        "completed",
        "skipped",
        "overdue",
    }


def test_session_mode_matches_spec() -> None:
    assert {e.value for e in SessionMode} == {
        "guided",
        "practice",
        "review",
        "assessment",
        "project",
        "interview",
        "socratic",
        "teach_back",
    }


def test_session_status_matches_spec() -> None:
    assert {e.value for e in SessionStatus} == {
        "planned",
        "active",
        "completed",
        "abandoned",
    }


def test_activity_type_matches_spec() -> None:
    assert {e.value for e in ActivityType} == {
        "recall",
        "explanation",
        "example",
        "exercise",
        "feedback",
        "reflection",
        "review",
        "project_task",
        "assessment",
    }


def test_activity_status_matches_spec() -> None:
    assert {e.value for e in ActivityStatus} == {
        "pending",
        "active",
        "completed",
        "skipped",
    }


def test_project_status_matches_spec() -> None:
    assert {e.value for e in ProjectStatus} == {
        "proposed",
        "active",
        "completed",
        "abandoned",
    }


def test_assessment_type_matches_spec() -> None:
    assert {e.value for e in AssessmentType} == {
        "diagnostic",
        "formative",
        "transfer",
        "final",
    }


def test_roadmap_status_matches_spec() -> None:
    assert {e.value for e in RoadmapStatus} == {"active", "superseded"}


def test_proposal_operation_has_no_delete_variant() -> None:
    """docs/AGENTS.md #6 / docs/TASKS.md T123 vault security audit:
    an AI-driven change proposal may create a file, update frontmatter,
    replace a managed section, or add a link -- never delete anything.
    Pinning the exact member set here means a future addition to this
    enum can't silently introduce a deletion capability without this
    test forcing a deliberate, visible decision."""
    assert {e.value for e in ProposalOperation} == {
        "create_file",
        "update_frontmatter",
        "replace_managed_section",
        "add_link",
    }


def test_all_enum_values_are_strings() -> None:
    all_enums = [
        TargetLevel,
        GoalStatus,
        ConceptStatus,
        ConceptRelationType,
        EvidenceSourceType,
        ExerciseType,
        MistakeType,
        MistakeSeverity,
        ReviewStatus,
        SessionMode,
        SessionStatus,
        ActivityType,
        ActivityStatus,
        ProjectStatus,
        ProposalOperation,
        AssessmentType,
        RoadmapStatus,
    ]
    for enum_cls in all_enums:
        for member in enum_cls:
            assert isinstance(member.value, str)
