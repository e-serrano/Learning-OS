"""T047: consolidating end-to-end tests across T037-T046.

Individual components already have thorough unit tests; this file proves
they work correctly *together* against a realistic vault: empty vault,
an existing vault with mixed content, malformed frontmatter not aborting
a scan, external changes, conflicts, and user-text preservation.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session as DbSession

from app.obsidian.atomic_writer import write_note
from app.obsidian.change_proposal import (
    ChangeProposal,
    ChangeProposalRepository,
    ProposalOperation,
    ProposalStatus,
)
from app.obsidian.conflict_detection import VaultConflictError, assert_no_conflict
from app.obsidian.diff_engine import generate_diff
from app.obsidian.managed_sections import get_section, replace_section
from app.obsidian.vault_index import VaultIndexer
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import VaultFileModel

MANAGED_NOTE = """---
id: concept_sql_window_functions
type: concept
managed_by: learning_os
mastery: 2.5
---
# SQL Window Functions

<!-- LEARNING_OS:BEGIN:SUMMARY -->
Old summary.
<!-- LEARNING_OS:END:SUMMARY -->

## My understanding

This is written by the user and must never be touched automatically.
"""


def _setup(tmp_path: Path):  # type: ignore[no-untyped-def]
    vault = tmp_path / "vault"
    vault.mkdir()
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    resolver = VaultResolver(str(vault))
    return vault, engine, resolver


def test_empty_vault_indexes_to_nothing_without_error(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)
    entries = VaultIndexer(engine, resolver).reindex()
    assert entries == []


def test_existing_vault_with_mixed_content_indexes_correctly(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)
    (vault / "plain.md").write_text("# Just a note\n")
    (vault / "concept.md").write_text(MANAGED_NOTE)
    (vault / "broken.md").write_text("---\nid: [unclosed\n---\nBody\n")

    entries = VaultIndexer(engine, resolver).reindex()

    assert {e.path for e in entries} == {"plain.md", "concept.md", "broken.md"}
    by_path = {e.path: e for e in entries}
    assert by_path["concept.md"].managed_id == "concept_sql_window_functions"
    assert by_path["plain.md"].managed_id is None
    assert by_path["broken.md"].managed_id is None  # malformed frontmatter didn't abort the scan


def test_malformed_frontmatter_in_one_file_does_not_block_others(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)
    (vault / "broken.md").write_text("---\n[not: valid: yaml: at all\n---\nBody\n")
    (vault / "fine.md").write_text("# Fine\n")

    entries = VaultIndexer(engine, resolver).reindex()

    assert len(entries) == 2  # both indexed despite one being malformed


def test_external_change_produces_conflict_that_blocks_write(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)
    note = vault / "concept.md"
    note.write_text(MANAGED_NOTE)
    VaultIndexer(engine, resolver).reindex()

    # Obsidian/the user edits the file directly, outside Learning OS
    note.write_text(MANAGED_NOTE.replace("Old summary.", "User rewrote this."))

    with pytest.raises(VaultConflictError):
        write_note(engine, resolver, "concept.md", "learning os overwrite attempt")

    # the external edit must survive untouched
    assert "User rewrote this." in note.read_text()


def test_full_curated_update_preserves_user_text_and_updates_index(tmp_path: Path) -> None:
    """Scan -> propose -> diff -> approve -> write -> verify, via a
    replace_managed_section change proposal -- the shape of the real
    knowledge-consolidation flow (docs/SPECS.md #16), minus the AI call."""
    vault, engine, resolver = _setup(tmp_path)
    note = vault / "concept.md"
    note.write_text(MANAGED_NOTE)
    indexer = VaultIndexer(engine, resolver)
    indexer.reindex()

    current = note.read_text()
    updated = replace_section(current, "SUMMARY", "Learner has now practiced 5 exercises.")

    diff = generate_diff(current, updated, path="concept.md")
    assert diff.has_changes is True

    proposals = ChangeProposalRepository(engine)
    with DbSession(engine) as db:
        hash_before = db.get(VaultFileModel, "concept.md").content_hash

    now = datetime.now(UTC)
    proposal = ChangeProposal(
        id="proposal_1",
        path="concept.md",
        operation=ProposalOperation.REPLACE_MANAGED_SECTION,
        section="SUMMARY",
        content="Learner has now practiced 5 exercises.",
        created_at=now,
        updated_at=now,
    )
    proposals.add(proposal)

    # user approves
    proposals.update_status("proposal_1", ProposalStatus.APPROVED)

    # apply: no conflict (nothing changed externally since index)
    assert_no_conflict(engine, resolver, "concept.md")
    write_note(engine, resolver, "concept.md", updated)
    proposals.update_status("proposal_1", ProposalStatus.APPLIED)

    final_content = note.read_text()
    assert get_section(final_content, "SUMMARY") == "Learner has now practiced 5 exercises."
    assert "This is written by the user and must never be touched automatically." in final_content

    applied = proposals.get("proposal_1")
    assert applied is not None
    assert applied.status == ProposalStatus.APPLIED
    assert applied.applied_at is not None

    with DbSession(engine) as db:
        row = db.get(VaultFileModel, "concept.md")
        assert row is not None
        assert row.content_hash != hash_before
