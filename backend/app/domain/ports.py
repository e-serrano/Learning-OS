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
    Concept,
    Evidence,
    Exercise,
    LearningGoal,
    Mistake,
    Review,
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


class EvidenceRepository(Protocol):
    """Append-only -- see docs/AGENTS.md #8. No update/delete method."""

    def add(self, evidence: Evidence) -> None: ...
    def list_by_concept(self, concept_id: str) -> list[Evidence]: ...
    def list_by_goal(self, goal_id: str) -> list[Evidence]: ...


class SessionRepository(Protocol):
    def add(self, session: Session) -> None: ...
    def get(self, session_id: str) -> Session | None: ...
    def update(self, session: Session) -> None: ...


class ExerciseRepository(Protocol):
    def add(self, exercise: Exercise) -> None: ...
    def get(self, exercise_id: str) -> Exercise | None: ...


class ReviewRepository(Protocol):
    def add(self, review: Review) -> None: ...
    def get(self, review_id: str) -> Review | None: ...
    def list_due(self, before: datetime) -> list[Review]: ...
    def update(self, review: Review) -> None: ...


class MistakeRepository(Protocol):
    def add(self, mistake: Mistake) -> None: ...
    def list_by_concept(self, concept_id: str) -> list[Mistake]: ...
    def update(self, mistake: Mistake) -> None: ...
