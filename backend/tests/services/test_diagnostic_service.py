from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import DiagnosticianResponse, DiagnosticItem
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Concept, LearningGoal
from app.domain.enums import ConceptStatus, EvidenceSourceType, GoalStatus, TargetLevel
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
from app.services.context_builder import ContextBuilder, GoalNotFoundError
from app.services.diagnostic_service import DiagnosticService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


class NeverCalledProvider:
    async def generate(self, request: object, response_model: object) -> object:
        raise AssertionError("AI provider must not be called")


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _seed_goal_and_concepts(engine: Engine, concept_ids: list[str]) -> None:
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
    concepts = SqlConceptRepository(engine)
    for concept_id in concept_ids:
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


def _seed_session_and_activity(engine: Engine) -> None:
    with DbSession(engine) as db:
        db.add(
            SessionModel(
                id="session_1",
                goal_id="goal_1",
                mode="assessment",
                objective="Diagnostic",
                status="planned",
                created_at=NOW.isoformat(),
            )
        )
        db.flush()
        db.add(
            ActivityModel(
                id="activity_1",
                session_id="session_1",
                type="assessment",
                sequence=1,
                status="pending",
                payload_json="{}",
                created_at=NOW.isoformat(),
            )
        )
        db.commit()


def _service(engine: Engine, provider: object, clock: FakeClock | None = None) -> DiagnosticService:
    goals = SqlGoalRepository(engine)
    evidence = SqlEvidenceRepository(engine)
    context_builder = ContextBuilder(
        goals=goals,
        concepts=SqlConceptRepository(engine),
        concept_relations=SqlConceptRelationRepository(engine),
        evidence=evidence,
        mistakes=SqlMistakeRepository(engine),
    )
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    return DiagnosticService(
        goals=goals,
        evidence=evidence,
        context_builder=context_builder,
        orchestrator=orchestrator,
        clock=clock or FakeClock(NOW),
        ids=FakeIdGenerator(),
    )


@pytest.mark.asyncio
async def test_generate_items_returns_the_ai_proposed_items(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concepts(engine, ["concept_1"])
    expected = [
        DiagnosticItem(
            concept_id="concept_1", evidence_type="recall", question="What is X?", difficulty=2
        )
    ]
    provider = MockProvider()
    provider.set_response(DiagnosticianResponse, DiagnosticianResponse(items=expected))
    service = _service(engine, provider)

    items = await service.generate_items("goal_1", ["concept_1"])

    assert items == expected


@pytest.mark.asyncio
async def test_generate_items_raises_when_goal_not_found_without_calling_ai(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)

    service = _service(engine, NeverCalledProvider())

    with pytest.raises(GoalNotFoundError):
        await service.generate_items("missing_goal", ["concept_1"])


@pytest.mark.asyncio
async def test_generate_items_merges_context_across_concepts_with_one_goal_item(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concepts(engine, ["concept_1", "concept_2"])
    captured_requests: list[AIRequest] = []

    def _capture(request: AIRequest) -> DiagnosticianResponse:
        captured_requests.append(request)
        return DiagnosticianResponse(items=[])

    provider = MockProvider()
    provider.set_response(DiagnosticianResponse, _capture)
    service = _service(engine, provider)

    await service.generate_items("goal_1", ["concept_1", "concept_2"])

    sent = captured_requests[0]
    goal_items = [item for item in sent.context if item["kind"] == "goal"]
    concept_items = [item for item in sent.context if item["kind"] == "concept"]
    assert len(goal_items) == 1
    assert {item["id"] for item in concept_items} == {"concept_1", "concept_2"}


def test_record_response_creates_evidence_with_assessment_source(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concepts(engine, ["concept_1"])
    _seed_session_and_activity(engine)
    service = _service(engine, MockProvider())

    evidence = service.record_response(
        goal_id="goal_1",
        concept_id="concept_1",
        activity_id="activity_1",
        evidence_type="recall",
        correctness=0.8,
        difficulty=2,
        question="What is a window function?",
    )

    assert evidence.source_type == EvidenceSourceType.ASSESSMENT
    assert evidence.correctness == 0.8
    assert evidence.reasoning is None
    assert evidence.transfer is None
    assert evidence.metadata == {
        "assessment_type": "diagnostic",
        "evidence_type": "recall",
        "question": "What is a window function?",
    }


def test_record_response_application_type_also_sets_reasoning(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concepts(engine, ["concept_1"])
    _seed_session_and_activity(engine)
    service = _service(engine, MockProvider())

    evidence = service.record_response(
        goal_id="goal_1",
        concept_id="concept_1",
        activity_id="activity_1",
        evidence_type="application",
        correctness=0.7,
        difficulty=3,
    )

    assert evidence.correctness == 0.7
    assert evidence.reasoning == 0.7
    assert evidence.transfer is None


def test_record_response_transfer_type_also_sets_transfer(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concepts(engine, ["concept_1"])
    _seed_session_and_activity(engine)
    service = _service(engine, MockProvider())

    evidence = service.record_response(
        goal_id="goal_1",
        concept_id="concept_1",
        activity_id="activity_1",
        evidence_type="transfer",
        correctness=0.9,
        difficulty=4,
    )

    assert evidence.correctness == 0.9
    assert evidence.transfer == 0.9
    assert evidence.reasoning is None


def test_record_response_persists_via_evidence_repository(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_goal_and_concepts(engine, ["concept_1"])
    _seed_session_and_activity(engine)
    service = _service(engine, MockProvider())

    created = service.record_response(
        goal_id="goal_1",
        concept_id="concept_1",
        activity_id="activity_1",
        evidence_type="recall",
        correctness=1.0,
        difficulty=1,
    )

    stored = SqlEvidenceRepository(engine).list_by_concept("concept_1")
    assert stored == [created]
