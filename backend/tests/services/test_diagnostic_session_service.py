from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import DiagnosticianResponse, DiagnosticItem
from app.ai.orchestrator import AIOrchestrator
from app.domain.entities import Concept, LearningGoal
from app.domain.enums import ConceptStatus, GoalStatus, TargetLevel
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories import (
    SqlActivityRepository,
    SqlConceptRelationRepository,
    SqlConceptRepository,
    SqlEvidenceRepository,
    SqlGoalRepository,
    SqlMistakeRepository,
    SqlSessionRepository,
)
from app.services.context_builder import ContextBuilder, GoalNotFoundError
from app.services.diagnostic_service import DiagnosticService
from app.services.diagnostic_session_service import (
    DiagnosticSessionService,
    NoConceptsForGoalError,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class FakeIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _seed_goal(engine: Engine) -> None:
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


def _seed_concept(engine: Engine, concept_id: str) -> None:
    concepts = SqlConceptRepository(engine)
    concepts.add(
        Concept(
            id=concept_id,
            title=concept_id,
            domain="sql",
            status=ConceptStatus.LEARNING,
            mastery=1,
            confidence=20,
            importance=3,
            retention=10,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    concepts.link_to_goal("goal_1", concept_id)


def _service(engine: Engine, provider: object) -> DiagnosticSessionService:
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    context_builder = ContextBuilder(
        goals=SqlGoalRepository(engine),
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        mistakes=SqlMistakeRepository(engine),
    )
    diagnostic = DiagnosticService(
        goals=SqlGoalRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        context_builder=context_builder,
        orchestrator=orchestrator,
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )
    return DiagnosticSessionService(
        goals=SqlGoalRepository(engine),
        concepts=SqlConceptRepository(engine),
        sessions=SqlSessionRepository(engine),
        activities=SqlActivityRepository(engine),
        diagnostic=diagnostic,
        clock=FakeClock(),
        ids=FakeIdGenerator(),
    )


def _response(**overrides: object) -> DiagnosticianResponse:
    defaults: dict[str, object] = dict(
        items=[
            DiagnosticItem(
                concept_id="window_functions",
                evidence_type="recall",
                question="What does ROW_NUMBER() do?",
                difficulty=2,
            )
        ]
    )
    defaults.update(overrides)
    return DiagnosticianResponse(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_start_diagnostic_creates_session_and_activities(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    _seed_concept(engine, "window_functions")
    provider = MockProvider()
    provider.set_response(DiagnosticianResponse, _response())

    result = await _service(engine, provider).start_diagnostic("goal_1")

    assert result.session.goal_id == "goal_1"
    assert result.session.status.value == "active"
    assert len(result.items) == 1
    item = result.items[0]
    assert item.concept_id == "window_functions"
    assert item.question == "What does ROW_NUMBER() do?"

    activities = SqlActivityRepository(engine).list_by_session(result.session.id)
    assert len(activities) == 1
    assert activities[0].id == item.activity_id
    assert activities[0].concept_ids == ["window_functions"]


@pytest.mark.asyncio
async def test_start_diagnostic_raises_when_goal_missing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()

    with pytest.raises(GoalNotFoundError):
        await _service(engine, provider).start_diagnostic("missing")


@pytest.mark.asyncio
async def test_start_diagnostic_raises_when_goal_has_no_concepts(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    provider = MockProvider()

    with pytest.raises(NoConceptsForGoalError):
        await _service(engine, provider).start_diagnostic("goal_1")


@pytest.mark.asyncio
async def test_start_diagnostic_creates_one_activity_per_item(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal(engine)
    _seed_concept(engine, "a")
    _seed_concept(engine, "b")
    provider = MockProvider()
    provider.set_response(
        DiagnosticianResponse,
        _response(
            items=[
                DiagnosticItem(concept_id="a", evidence_type="recall", question="Q1", difficulty=1),
                DiagnosticItem(
                    concept_id="b", evidence_type="transfer", question="Q2", difficulty=3
                ),
            ]
        ),
    )

    result = await _service(engine, provider).start_diagnostic("goal_1")

    assert len(result.items) == 2
    activities = SqlActivityRepository(engine).list_by_session(result.session.id)
    assert {a.sequence for a in activities} == {1, 2}
