from datetime import UTC, datetime
from uuid import uuid4

from app.ai.adapters.mock import MockProvider
from app.ai.protocol import AIProvider
from app.domain.entities import Concept, Evidence, Exercise, LearningGoal, Mistake, Review, Session
from app.domain.ports import (
    ClockPort,
    ConceptRepository,
    EvidenceRepository,
    ExerciseRepository,
    GoalRepository,
    IdGeneratorPort,
    MistakeRepository,
    ReviewRepository,
    SessionRepository,
    VaultPort,
    VaultScanSummary,
)


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidGenerator:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid4().hex}"


class FakeGoalRepository:
    def __init__(self) -> None:
        self._store: dict[str, LearningGoal] = {}

    def add(self, goal: LearningGoal) -> None:
        self._store[goal.id] = goal

    def get(self, goal_id: str) -> LearningGoal | None:
        return self._store.get(goal_id)

    def list_all(self) -> list[LearningGoal]:
        return list(self._store.values())

    def update(self, goal: LearningGoal) -> None:
        self._store[goal.id] = goal


class FakeConceptRepository:
    def __init__(self) -> None:
        self._store: dict[str, Concept] = {}

    def add(self, concept: Concept) -> None:
        self._store[concept.id] = concept

    def get(self, concept_id: str) -> Concept | None:
        return self._store.get(concept_id)

    def list_by_goal(self, goal_id: str) -> list[Concept]:
        return list(self._store.values())

    def list_due_for_review(self, before: datetime) -> list[Concept]:
        return [c for c in self._store.values() if c.next_review and c.next_review <= before]

    def update(self, concept: Concept) -> None:
        self._store[concept.id] = concept


class FakeEvidenceRepository:
    def __init__(self) -> None:
        self._store: list[Evidence] = []

    def add(self, evidence: Evidence) -> None:
        self._store.append(evidence)

    def list_by_concept(self, concept_id: str) -> list[Evidence]:
        return [e for e in self._store if e.concept_id == concept_id]

    def list_by_goal(self, goal_id: str) -> list[Evidence]:
        return [e for e in self._store if e.goal_id == goal_id]


class FakeSessionRepository:
    def __init__(self) -> None:
        self._store: dict[str, Session] = {}

    def add(self, session: Session) -> None:
        self._store[session.id] = session

    def get(self, session_id: str) -> Session | None:
        return self._store.get(session_id)

    def list_by_goal(self, goal_id: str) -> list[Session]:
        return [s for s in self._store.values() if s.goal_id == goal_id]

    def update(self, session: Session) -> None:
        self._store[session.id] = session


class FakeExerciseRepository:
    def __init__(self) -> None:
        self._store: dict[str, Exercise] = {}

    def add(self, exercise: Exercise) -> None:
        self._store[exercise.id] = exercise

    def get(self, exercise_id: str) -> Exercise | None:
        return self._store.get(exercise_id)


class FakeReviewRepository:
    def __init__(self) -> None:
        self._store: dict[str, Review] = {}

    def add(self, review: Review) -> None:
        self._store[review.id] = review

    def get(self, review_id: str) -> Review | None:
        return self._store.get(review_id)

    def list_due(self, before: datetime) -> list[Review]:
        return [r for r in self._store.values() if r.scheduled_at <= before]

    def update(self, review: Review) -> None:
        self._store[review.id] = review


class FakeMistakeRepository:
    def __init__(self) -> None:
        self._store: dict[str, Mistake] = {}

    def add(self, mistake: Mistake) -> None:
        self._store[mistake.id] = mistake

    def list_by_concept(self, concept_id: str) -> list[Mistake]:
        return [m for m in self._store.values() if m.concept_id == concept_id]

    def update(self, mistake: Mistake) -> None:
        self._store[mistake.id] = mistake


class FakeVault:
    def scan_readonly(self, path: str) -> VaultScanSummary:
        return VaultScanSummary(exists=True, readable=True, markdown_file_count=0, errors=[])


def _accepts_clock(port: ClockPort) -> ClockPort:
    return port


def _accepts_id_generator(port: IdGeneratorPort) -> IdGeneratorPort:
    return port


def _accepts_vault(port: VaultPort) -> VaultPort:
    return port


def _accepts_goal_repo(port: GoalRepository) -> GoalRepository:
    return port


def _accepts_concept_repo(port: ConceptRepository) -> ConceptRepository:
    return port


def _accepts_evidence_repo(port: EvidenceRepository) -> EvidenceRepository:
    return port


def _accepts_session_repo(port: SessionRepository) -> SessionRepository:
    return port


def _accepts_exercise_repo(port: ExerciseRepository) -> ExerciseRepository:
    return port


def _accepts_review_repo(port: ReviewRepository) -> ReviewRepository:
    return port


def _accepts_mistake_repo(port: MistakeRepository) -> MistakeRepository:
    return port


def _accepts_ai_provider(port: AIProvider) -> AIProvider:
    return port


def test_clock_port_is_satisfied_by_system_clock() -> None:
    clock = _accepts_clock(SystemClock())
    assert isinstance(clock.now(), datetime)


def test_id_generator_port_is_satisfied_by_uuid_generator() -> None:
    generator = _accepts_id_generator(UuidGenerator())
    assert generator.new_id("goal").startswith("goal_")


def test_vault_port_is_satisfied_by_fake_vault() -> None:
    vault = _accepts_vault(FakeVault())
    result = vault.scan_readonly("/some/path")
    assert result.exists is True


def test_all_repository_ports_are_satisfied_by_fakes() -> None:
    _accepts_goal_repo(FakeGoalRepository())
    _accepts_concept_repo(FakeConceptRepository())
    _accepts_evidence_repo(FakeEvidenceRepository())
    _accepts_session_repo(FakeSessionRepository())
    _accepts_exercise_repo(FakeExerciseRepository())
    _accepts_review_repo(FakeReviewRepository())
    _accepts_mistake_repo(FakeMistakeRepository())


def test_existing_ai_provider_protocol_is_the_ai_port() -> None:
    """T017's AIProvider already satisfies T032's 'AI' port requirement."""
    _accepts_ai_provider(MockProvider())


def test_fake_goal_repository_roundtrips() -> None:
    repo = FakeGoalRepository()
    goal = LearningGoal(
        id="goal_1",
        title="Learn BigQuery",
        target_level="professional",  # type: ignore[arg-type]
        status="draft",  # type: ignore[arg-type]
        priority=3,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    repo.add(goal)
    assert repo.get("goal_1") == goal
    assert repo.list_all() == [goal]
