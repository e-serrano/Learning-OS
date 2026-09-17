"""Knowledge E2E (docs/TASKS.md T085): session -> proposal -> diff ->
approval -> Markdown updated without losing text, exercising every
service built in T080-T084 against a real SQLite-backed stack and a
real vault directory on disk.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import CuratorOperation, CuratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.domain.entities import Concept, Evidence, LearningGoal
from app.domain.enums import (
    ConceptStatus,
    EvidenceSourceType,
    GoalStatus,
    ProposalOperation,
    TargetLevel,
)
from app.obsidian.change_proposal import ChangeProposalRepository, ProposalStatus
from app.obsidian.diff_engine import generate_diff
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import ActivityModel, SessionModel
from app.persistence.repositories import (
    SqlConceptRepository,
    SqlEvidenceRepository,
    SqlGoalRepository,
)
from app.services.apply_change_service import ApplyChangeService
from app.services.curator_service import CuratorService
from app.services.diff_approval_service import DiffApprovalService
from app.services.proposal_validator import ProposalValidator

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class SequentialIdGenerator:
    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    def new_id(self, prefix: str) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}_{self._counters[prefix]}"


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _seed_session_and_activity(engine: Engine) -> None:
    with DbSession(engine) as db:
        db.add(
            SessionModel(
                id="session_1",
                goal_id="goal_1",
                mode="guided",
                objective="Practice",
                status="active",
                started_at=NOW.isoformat(),
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
                status="completed",
                payload_json="{}",
                created_at=NOW.isoformat(),
            )
        )
        db.commit()


@pytest.mark.asyncio
async def test_knowledge_flow_end_to_end(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    vault = VaultResolver(str(vault_root))
    ids = SequentialIdGenerator()
    clock = FixedClock()

    goals = SqlGoalRepository(engine)
    concepts = SqlConceptRepository(engine)
    evidence = SqlEvidenceRepository(engine)
    proposals = ChangeProposalRepository(engine)

    provider = MockProvider()
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]

    curator_service = CuratorService(goals, concepts, evidence, vault, orchestrator)
    validator = ProposalValidator(proposals, vault, clock, ids)
    approval_service = DiffApprovalService(proposals)
    apply_service = ApplyChangeService(engine, proposals, vault)

    # -- a session already happened, producing evidence for the concept
    goals.add(
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
    concepts.add(
        Concept(
            id="window_functions",
            title="Window Functions",
            domain="sql",
            status=ConceptStatus.USABLE,
            mastery=3.5,
            confidence=70,
            importance=4,
            retention=60,
            obsidian_path="window_functions.md",
            created_at=NOW,
            updated_at=NOW,
        )
    )
    _seed_session_and_activity(engine)
    evidence.add(
        Evidence(
            id="evidence_1",
            concept_id="window_functions",
            goal_id="goal_1",
            session_id="session_1",
            activity_id="activity_1",
            source_type=EvidenceSourceType.EXERCISE,
            difficulty=3,
            correctness=0.9,
            timestamp=NOW,
        )
    )

    # -- the note already has hand-authored content outside any managed section
    hand_authored = (
        "# Window Functions\n\n"
        "<!-- LEARNING_OS:BEGIN:SUMMARY -->\nOld, outdated summary.\n"
        "<!-- LEARNING_OS:END:SUMMARY -->\n\n"
        "## My examples\n"
        "```sql\nSELECT ROW_NUMBER() OVER (ORDER BY id) FROM my_table;\n```\n\n"
        "## Questions\n- Why does PARTITION BY change the result?\n"
    )
    (vault_root / "window_functions.md").write_text(hand_authored, encoding="utf-8")

    # -- curator proposes an update (T080)
    provider.set_response(
        CuratorResponse,
        CuratorResponse(
            operations=[
                CuratorOperation(
                    path="window_functions.md",
                    operation=ProposalOperation.REPLACE_MANAGED_SECTION,
                    section="SUMMARY",
                    content="Window functions compute a value across a set of related rows "
                    "without collapsing them, using OVER() with PARTITION BY/ORDER BY.",
                )
            ]
        ),
    )
    operations = await curator_service.propose(
        "goal_1", "window_functions", session_outcome="Solved a ROW_NUMBER exercise correctly."
    )
    assert len(operations) == 1

    # -- validate and persist as a pending proposal (T081)
    concept = concepts.get("window_functions")
    assert concept is not None
    validation = validator.validate_and_persist(operations, concept)
    assert validation.rejected == []
    proposal = validation.accepted[0]
    assert proposal.status == ProposalStatus.PENDING

    # -- diff preview before any approval decision (T085: "diff" step)
    before = (vault_root / "window_functions.md").read_text(encoding="utf-8")
    after = apply_service.compute_content(proposal)
    diff = generate_diff(before, after, proposal.path)
    assert diff.has_changes
    assert "Old, outdated summary." not in after
    assert "## My examples" in after  # hand-authored content untouched in the preview too

    # -- approve (T082)
    approved = approval_service.approve(proposal.id)
    assert approved.status == ProposalStatus.APPROVED

    # -- apply, which also runs write verification (T083, T084)
    applied = apply_service.apply(proposal.id)
    assert applied.status == ProposalStatus.APPLIED

    # -- final Markdown: new summary landed, hand-authored text survived untouched
    final_content = (vault_root / "window_functions.md").read_text(encoding="utf-8")
    assert "Old, outdated summary." not in final_content
    assert "without collapsing them" in final_content
    assert "## My examples" in final_content
    assert "SELECT ROW_NUMBER() OVER (ORDER BY id) FROM my_table;" in final_content
    assert "## Questions" in final_content
    assert "Why does PARTITION BY change the result?" in final_content
