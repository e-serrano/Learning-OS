from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import CuratorOperation, CuratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Concept, Evidence, LearningGoal
from app.domain.enums import (
    ConceptStatus,
    EvidenceSourceType,
    GoalStatus,
    ProposalOperation,
    TargetLevel,
)
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import ActivityModel, SessionModel
from app.persistence.repositories import (
    SqlConceptRepository,
    SqlEvidenceRepository,
    SqlGoalRepository,
)
from app.services.context_builder import ConceptNotFoundError, GoalNotFoundError
from app.services.curator_service import CuratorService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class NeverCalledProvider:
    async def generate(self, request: object, response_model: object) -> object:
        raise AssertionError("AI provider must not be called")


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _seed_goal_and_concept(engine: Engine, **concept_overrides: object) -> None:
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
    defaults: dict[str, object] = dict(
        id="concept_1",
        title="Window Functions",
        domain="sql",
        status=ConceptStatus.LEARNING,
        mastery=2,
        confidence=40,
        importance=3,
        retention=30,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(concept_overrides)
    SqlConceptRepository(engine).add(Concept(**defaults))  # type: ignore[arg-type]


def _seed_session_and_activity(engine: Engine) -> None:
    with DbSession(engine) as db:
        db.add(
            SessionModel(
                id="session_1",
                goal_id="goal_1",
                mode="guided",
                objective="Practice",
                status="active",
                created_at=NOW.isoformat(),
            )
        )
        db.flush()
        db.add(
            ActivityModel(
                id="activity_1",
                session_id="session_1",
                type="exercise",
                sequence=1,
                status="active",
                payload_json="{}",
                created_at=NOW.isoformat(),
            )
        )
        db.commit()


def _service(engine: Engine, provider: object, vault_root: Path) -> CuratorService:
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]
    return CuratorService(
        goals=SqlGoalRepository(engine),
        concepts=SqlConceptRepository(engine),
        evidence=SqlEvidenceRepository(engine),
        vault=VaultResolver(str(vault_root)),
        orchestrator=orchestrator,
    )


def _curator_response(**overrides: object) -> CuratorResponse:
    defaults: dict[str, object] = dict(
        operations=[
            CuratorOperation(
                path="concepts/window_functions.md",
                operation=ProposalOperation.REPLACE_MANAGED_SECTION,
                section="SUMMARY",
                content="Window functions compute values across row sets.",
            )
        ]
    )
    defaults.update(overrides)
    return CuratorResponse(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_propose_returns_the_ai_proposed_operations(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    _seed_goal_and_concept(engine)
    expected = _curator_response()
    provider = MockProvider()
    provider.set_response(CuratorResponse, expected)
    service = _service(engine, provider, vault_root)

    operations = await service.propose("goal_1", "concept_1")

    assert operations == expected.operations


@pytest.mark.asyncio
async def test_propose_raises_when_goal_not_found_without_calling_ai(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    service = _service(engine, NeverCalledProvider(), vault_root)

    with pytest.raises(GoalNotFoundError):
        await service.propose("missing_goal", "concept_1")


@pytest.mark.asyncio
async def test_propose_raises_when_concept_not_found_without_calling_ai(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
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
    service = _service(engine, NeverCalledProvider(), vault_root)

    with pytest.raises(ConceptNotFoundError):
        await service.propose("goal_1", "missing_concept")


@pytest.mark.asyncio
async def test_propose_reads_the_existing_note_content_into_the_request(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    _seed_goal_and_concept(engine, obsidian_path="window_functions.md")
    note_path = vault_root / "window_functions.md"
    note_path.write_text("# Window Functions\n\nExisting notes.\n", encoding="utf-8")
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> CuratorResponse:
        captured.append(request)
        return _curator_response()

    provider = MockProvider()
    provider.set_response(CuratorResponse, _capture)
    service = _service(engine, provider, vault_root)

    await service.propose("goal_1", "concept_1")

    sent = captured[0]
    assert sent.current_state["target_note"] == "window_functions.md"
    assert sent.current_state["current_note"] == "# Window Functions\n\nExisting notes.\n"


@pytest.mark.asyncio
async def test_propose_current_note_is_empty_string_for_a_new_note(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    _seed_goal_and_concept(engine, obsidian_path=None)
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> CuratorResponse:
        captured.append(request)
        return _curator_response()

    provider = MockProvider()
    provider.set_response(CuratorResponse, _capture)
    service = _service(engine, provider, vault_root)

    await service.propose("goal_1", "concept_1")

    sent = captured[0]
    assert sent.current_state["target_note"] == "concept_1.md"
    assert sent.current_state["current_note"] == ""


@pytest.mark.asyncio
async def test_propose_includes_recent_evidence_in_the_context(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    _seed_goal_and_concept(engine)
    _seed_session_and_activity(engine)
    SqlEvidenceRepository(engine).add(
        Evidence(
            id="evidence_1",
            concept_id="concept_1",
            goal_id="goal_1",
            activity_id="activity_1",
            source_type=EvidenceSourceType.EXERCISE,
            difficulty=3,
            correctness=0.8,
            timestamp=NOW,
        )
    )
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> CuratorResponse:
        captured.append(request)
        return _curator_response()

    provider = MockProvider()
    provider.set_response(CuratorResponse, _capture)
    service = _service(engine, provider, vault_root)

    await service.propose("goal_1", "concept_1")

    evidence_items = [item for item in captured[0].context if item["kind"] == "evidence"]
    assert len(evidence_items) == 1
    assert evidence_items[0]["correctness"] == 0.8


@pytest.mark.asyncio
async def test_propose_passes_through_session_outcome(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    _seed_goal_and_concept(engine)
    captured: list[AIRequest] = []

    def _capture(request: AIRequest) -> CuratorResponse:
        captured.append(request)
        return _curator_response()

    provider = MockProvider()
    provider.set_response(CuratorResponse, _capture)
    service = _service(engine, provider, vault_root)

    await service.propose(
        "goal_1", "concept_1", session_outcome="Completed 3 exercises, 2 correct."
    )

    assert captured[0].task["session_outcome"] == "Completed 3 exercises, 2 correct."
