"""Ports (interfaces) the domain depends on -- concrete adapters are built
in later tasks: repositories in T035, the vault adapter in T037+, AI
adapters in T051-T056.

Domain code depends only on these Protocols, never on SQLAlchemy, the
filesystem, or a provider SDK directly (docs/AGENTS.md #4).

The AI port is not redeclared here -- app.ai.protocol.AIProvider (built in
T017) already is that port; see docs/AI_CONTRACTS.md #3.
"""

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel

from app.domain.entities import (
    Activity,
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
)


class ClockPort(Protocol):
    def now(self) -> datetime: ...


class IdGeneratorPort(Protocol):
    def new_id(self, prefix: str) -> str: ...


class VaultScanSummary(BaseModel):
    """Domain-level shape for a read-only vault scan result.

    Structurally mirrors app.obsidian.onboarding_scan.VaultScanResult, kept
    separate so this module never imports the obsidian adapter package.
    Reconciled when T037 builds the full vault resolver.
    """

    exists: bool
    readable: bool
    markdown_file_count: int
    errors: list[str]


class VaultPort(Protocol):
    def scan_readonly(self, path: str) -> VaultScanSummary: ...


class GoalRepository(Protocol):
    def add(self, goal: LearningGoal) -> None: ...
    def get(self, goal_id: str) -> LearningGoal | None: ...
    def list_all(self) -> list[LearningGoal]: ...
    def update(self, goal: LearningGoal) -> None: ...


class ConceptRepository(Protocol):
    def add(self, concept: Concept) -> None: ...
    def get(self, concept_id: str) -> Concept | None: ...
    def list_by_goal(self, goal_id: str) -> list[Concept]: ...
    def list_due_for_review(self, before: datetime) -> list[Concept]: ...
    def update(self, concept: Concept) -> None: ...
    def link_to_goal(self, goal_id: str, concept_id: str, importance: int = 3) -> None: ...


class ConceptRelationRepository(Protocol):
    """concept_relations -- see docs/DATABASE_SCHEMA.md #2. Table already
    existed since T033; this port/adapter was added in T060 for the
    context builder's prerequisite-relationship signal."""

    def add(self, relation: ConceptRelation) -> None: ...
    def list_prerequisites_of(self, concept_id: str) -> list[ConceptRelation]: ...
    def list_relations_from(self, concept_id: str) -> list[ConceptRelation]: ...


class EvidenceRepository(Protocol):
    """Append-only -- see docs/AGENTS.md #8. No update/delete method."""

    def add(self, evidence: Evidence) -> None: ...
    def list_by_concept(self, concept_id: str) -> list[Evidence]: ...
    def list_by_goal(self, goal_id: str) -> list[Evidence]: ...


class SessionRepository(Protocol):
    def add(self, session: Session) -> None: ...
    def get(self, session_id: str) -> Session | None: ...
    def list_by_goal(self, goal_id: str) -> list[Session]: ...
    def update(self, session: Session) -> None: ...


class ActivityRepository(Protocol):
    """activities -- see docs/DATABASE_SCHEMA.md. Table/model existed
    since T033; this port/adapter was added in T070 for next-activity
    selection to have somewhere to persist its pick."""

    def add(self, activity: Activity) -> None: ...
    def get(self, activity_id: str) -> Activity | None: ...
    def list_by_session(self, session_id: str) -> list[Activity]: ...
    def update(self, activity: Activity) -> None: ...


class ExerciseRepository(Protocol):
    def add(self, exercise: Exercise) -> None: ...
    def get(self, exercise_id: str) -> Exercise | None: ...
    def list_by_concept(self, concept_id: str) -> list[Exercise]: ...


class ExerciseAttemptRepository(Protocol):
    """exercise_attempts -- see docs/DATABASE_SCHEMA.md. Table/model
    existed since T033; this port/adapter was added in T072 for answer
    submission to have somewhere to persist an attempt."""

    def add(self, attempt: ExerciseAttempt) -> None: ...
    def get(self, attempt_id: str) -> ExerciseAttempt | None: ...


class EvaluationRepository(Protocol):
    """evaluations -- immutable like Evidence (docs/AGENTS.md #23), no
    update/delete. Table/model existed since T033; this port/adapter was
    added in T073 for the evaluator to have somewhere to persist its
    judgment."""

    def add(self, evaluation: Evaluation) -> None: ...
    def get(self, evaluation_id: str) -> Evaluation | None: ...


class ReviewRepository(Protocol):
    def add(self, review: Review) -> None: ...
    def get(self, review_id: str) -> Review | None: ...
    def list_due(self, before: datetime) -> list[Review]: ...
    def list_by_concept(self, concept_id: str) -> list[Review]: ...
    def update(self, review: Review) -> None: ...


class MistakeRepository(Protocol):
    def add(self, mistake: Mistake) -> None: ...
    def list_by_concept(self, concept_id: str) -> list[Mistake]: ...
    def update(self, mistake: Mistake) -> None: ...


class ProjectRepository(Protocol):
    """projects -- see docs/DATABASE_SCHEMA.md (T092 gap fix)."""

    def add(self, project: Project) -> None: ...
    def get(self, project_id: str) -> Project | None: ...
    def list_by_goal(self, goal_id: str) -> list[Project]: ...
    def update(self, project: Project) -> None: ...


class RoadmapRepository(Protocol):
    """roadmaps -- see docs/DATABASE_SCHEMA.md (T068 gap fix). Only one
    roadmap is `active` per goal at a time (docs/DOMAIN_MODEL.md #3)."""

    def add(self, roadmap: Roadmap) -> None: ...
    def get_active_for_goal(self, goal_id: str) -> Roadmap | None: ...
    def update(self, roadmap: Roadmap) -> None: ...
