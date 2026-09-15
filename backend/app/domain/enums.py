from enum import StrEnum


class TargetLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PROFESSIONAL = "professional"


class GoalStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ConceptStatus(StrEnum):
    UNKNOWN = "unknown"
    LEARNING = "learning"
    WEAK = "weak"
    DEVELOPING = "developing"
    USABLE = "usable"
    STRONG = "strong"
    MASTERED = "mastered"
    NEEDS_REVIEW = "needs_review"
    DEPRECATED = "deprecated"


class ConceptRelationType(StrEnum):
    """See docs/DATABASE_SCHEMA.md #2 concept_relations -- stored uppercase."""

    PREREQUISITE_OF = "PREREQUISITE_OF"
    RELATED_TO = "RELATED_TO"
    PART_OF = "PART_OF"
    CONTRASTS_WITH = "CONTRASTS_WITH"
    APPLIED_BY = "APPLIED_BY"


class EvidenceSourceType(StrEnum):
    EXERCISE = "exercise"
    ASSESSMENT = "assessment"
    TEACH_BACK = "teach_back"
    PROJECT = "project"
    REVIEW = "review"
    SELF_REPORT = "self_report"


class ExerciseType(StrEnum):
    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"
    TEACH_BACK = "teach_back"
    CODING = "coding"
    SQL = "sql"
    DEBUGGING = "debugging"
    DESIGN = "design"
    DECISION = "decision"
    SCENARIO = "scenario"
    COMPARISON = "comparison"
    PREDICTION = "prediction"


class MistakeType(StrEnum):
    MISCONCEPTION = "misconception"
    PROCEDURE = "procedure"
    RECALL = "recall"
    REASONING = "reasoning"
    ATTENTION = "attention"
    CALIBRATION = "calibration"


class MistakeSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReviewStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    OVERDUE = "overdue"


class SessionMode(StrEnum):
    GUIDED = "guided"
    PRACTICE = "practice"
    REVIEW = "review"
    ASSESSMENT = "assessment"
    PROJECT = "project"
    INTERVIEW = "interview"
    SOCRATIC = "socratic"
    TEACH_BACK = "teach_back"


class SessionStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ActivityType(StrEnum):
    RECALL = "recall"
    EXPLANATION = "explanation"
    EXAMPLE = "example"
    EXERCISE = "exercise"
    FEEDBACK = "feedback"
    REFLECTION = "reflection"
    REVIEW = "review"
    PROJECT_TASK = "project_task"
    ASSESSMENT = "assessment"


class ActivityStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class ProjectStatus(StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class AssessmentType(StrEnum):
    DIAGNOSTIC = "diagnostic"
    FORMATIVE = "formative"
    TRANSFER = "transfer"
    FINAL = "final"


class RoadmapStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class ProposalOperation(StrEnum):
    """The only Obsidian write operations a proposal may request -- see
    docs/AGENTS.md #6 (AI-generated file operations are data, not
    executable instructions). Shared by app.ai (curator responses) and
    app.obsidian (change proposals) so neither depends on the other."""

    CREATE_FILE = "create_file"
    UPDATE_FRONTMATTER = "update_frontmatter"
    REPLACE_MANAGED_SECTION = "replace_managed_section"
    ADD_LINK = "add_link"
