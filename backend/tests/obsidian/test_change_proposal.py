from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.obsidian.change_proposal import (
    ChangeProposal,
    ChangeProposalRepository,
    ProposalOperation,
    ProposalStatus,
)
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine

NOW = datetime.now(UTC)


def _engine(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _make_proposal(**overrides: object) -> ChangeProposal:
    defaults: dict[str, object] = dict(
        id="proposal_1",
        path="Concepts/note.md",
        operation=ProposalOperation.REPLACE_MANAGED_SECTION,
        section="SUMMARY",
        content="New summary.",
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return ChangeProposal(**defaults)  # type: ignore[arg-type]


def test_operation_enum_is_limited_to_four_values() -> None:
    assert {op.value for op in ProposalOperation} == {
        "create_file",
        "update_frontmatter",
        "replace_managed_section",
        "add_link",
    }


def test_status_enum_matches_spec() -> None:
    assert {s.value for s in ProposalStatus} == {
        "pending",
        "approved",
        "rejected",
        "applied",
        "conflicted",
        "failed",
    }


def test_new_proposal_defaults_to_pending() -> None:
    proposal = _make_proposal()
    assert proposal.status == ProposalStatus.PENDING
    assert proposal.error is None
    assert proposal.applied_at is None


def test_add_then_get_roundtrips(tmp_path: Path) -> None:
    repo = ChangeProposalRepository(_engine(tmp_path))
    proposal = _make_proposal()
    repo.add(proposal)

    assert repo.get("proposal_1") == proposal


def test_get_missing_returns_none(tmp_path: Path) -> None:
    repo = ChangeProposalRepository(_engine(tmp_path))
    assert repo.get("does-not-exist") is None


def test_list_by_status_filters_correctly(tmp_path: Path) -> None:
    repo = ChangeProposalRepository(_engine(tmp_path))
    repo.add(_make_proposal(id="p1"))
    repo.add(_make_proposal(id="p2", status=ProposalStatus.APPROVED))

    pending = repo.list_by_status(ProposalStatus.PENDING)
    assert {p.id for p in pending} == {"p1"}


def test_update_status_to_approved(tmp_path: Path) -> None:
    repo = ChangeProposalRepository(_engine(tmp_path))
    repo.add(_make_proposal())

    repo.update_status("proposal_1", ProposalStatus.APPROVED)

    loaded = repo.get("proposal_1")
    assert loaded is not None
    assert loaded.status == ProposalStatus.APPROVED


def test_update_status_to_applied_sets_applied_at(tmp_path: Path) -> None:
    repo = ChangeProposalRepository(_engine(tmp_path))
    repo.add(_make_proposal())

    repo.update_status("proposal_1", ProposalStatus.APPLIED)

    loaded = repo.get("proposal_1")
    assert loaded is not None
    assert loaded.applied_at is not None


def test_update_status_to_conflicted_records_error(tmp_path: Path) -> None:
    repo = ChangeProposalRepository(_engine(tmp_path))
    repo.add(_make_proposal())

    repo.update_status("proposal_1", ProposalStatus.CONFLICTED, error="hash mismatch")

    loaded = repo.get("proposal_1")
    assert loaded is not None
    assert loaded.status == ProposalStatus.CONFLICTED
    assert loaded.error == "hash mismatch"


def test_update_status_on_missing_proposal_raises(tmp_path: Path) -> None:
    repo = ChangeProposalRepository(_engine(tmp_path))
    with pytest.raises(ValueError, match="does-not-exist"):
        repo.update_status("does-not-exist", ProposalStatus.REJECTED)


def test_create_file_operation_needs_no_section(tmp_path: Path) -> None:
    repo = ChangeProposalRepository(_engine(tmp_path))
    proposal = _make_proposal(id="p_create", operation=ProposalOperation.CREATE_FILE, section=None)
    repo.add(proposal)

    loaded = repo.get("p_create")
    assert loaded is not None
    assert loaded.section is None
