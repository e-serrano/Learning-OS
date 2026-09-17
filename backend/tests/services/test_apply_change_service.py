from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.domain.enums import ProposalOperation
from app.obsidian.change_proposal import ChangeProposal, ChangeProposalRepository, ProposalStatus
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import VaultFileModel
from app.services.apply_change_service import ApplyChangeService, ProposalNotApprovedError
from app.services.diff_approval_service import ProposalNotFoundError

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _proposal(**overrides: object) -> ChangeProposal:
    defaults: dict[str, object] = dict(
        id="proposal_1",
        path="concept_1.md",
        operation=ProposalOperation.CREATE_FILE,
        section=None,
        content="# Concept 1\n",
        status=ProposalStatus.APPROVED,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return ChangeProposal(**defaults)  # type: ignore[arg-type]


def _service(tmp_path: Path) -> tuple[ApplyChangeService, ChangeProposalRepository, Path, Engine]:
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    engine = _engine(tmp_path)
    proposals = ChangeProposalRepository(engine)
    service = ApplyChangeService(engine, proposals, VaultResolver(str(vault_root)))
    return service, proposals, vault_root, engine


def test_apply_create_file_writes_new_file_and_marks_applied(tmp_path: Path) -> None:
    service, proposals, vault_root, _engine_instance = _service(tmp_path)
    proposals.add(_proposal())

    result = service.apply("proposal_1")

    assert result.status == ProposalStatus.APPLIED
    assert (vault_root / "concept_1.md").read_text(encoding="utf-8") == "# Concept 1\n"


def test_apply_create_file_on_existing_file_fails_without_overwriting(tmp_path: Path) -> None:
    service, proposals, vault_root, _engine_instance = _service(tmp_path)
    (vault_root / "concept_1.md").write_text("original\n", encoding="utf-8")
    proposals.add(_proposal())

    result = service.apply("proposal_1")

    assert result.status == ProposalStatus.FAILED
    assert result.error is not None and "already exists" in result.error
    assert (vault_root / "concept_1.md").read_text(encoding="utf-8") == "original\n"


def test_apply_replace_managed_section_creates_file_when_absent(tmp_path: Path) -> None:
    service, proposals, vault_root, _engine_instance = _service(tmp_path)
    proposals.add(
        _proposal(
            operation=ProposalOperation.REPLACE_MANAGED_SECTION,
            section="SUMMARY",
            content="Generated summary.",
        )
    )

    result = service.apply("proposal_1")

    assert result.status == ProposalStatus.APPLIED
    written = (vault_root / "concept_1.md").read_text(encoding="utf-8")
    assert "<!-- LEARNING_OS:BEGIN:SUMMARY -->" in written
    assert "Generated summary." in written


def test_apply_replace_managed_section_preserves_content_outside_the_section(
    tmp_path: Path,
) -> None:
    service, proposals, vault_root, _engine_instance = _service(tmp_path)
    (vault_root / "concept_1.md").write_text(
        "# My notes\n\n"
        "<!-- LEARNING_OS:BEGIN:SUMMARY -->\nOld summary.\n<!-- LEARNING_OS:END:SUMMARY -->\n\n"
        "## My examples\nHand-written.\n",
        encoding="utf-8",
    )
    proposals.add(
        _proposal(
            operation=ProposalOperation.REPLACE_MANAGED_SECTION,
            section="SUMMARY",
            content="New summary.",
        )
    )

    service.apply("proposal_1")

    written = (vault_root / "concept_1.md").read_text(encoding="utf-8")
    assert "New summary." in written
    assert "Old summary." not in written
    assert "# My notes" in written
    assert "## My examples\nHand-written." in written


def test_apply_update_frontmatter_replaces_block_and_keeps_body(tmp_path: Path) -> None:
    service, proposals, vault_root, _engine_instance = _service(tmp_path)
    (vault_root / "concept_1.md").write_text(
        "---\nstatus: learning\n---\n# My notes\nHand-written.\n", encoding="utf-8"
    )
    proposals.add(
        _proposal(
            operation=ProposalOperation.UPDATE_FRONTMATTER,
            content="status: usable\nmastery: 3.5",
        )
    )

    service.apply("proposal_1")

    written = (vault_root / "concept_1.md").read_text(encoding="utf-8")
    assert written == "---\nstatus: usable\nmastery: 3.5\n---\n# My notes\nHand-written.\n"


def test_apply_add_link_appends_to_the_end_of_the_file(tmp_path: Path) -> None:
    service, proposals, vault_root, _engine_instance = _service(tmp_path)
    (vault_root / "concept_1.md").write_text("# My notes\nSome text.\n", encoding="utf-8")
    proposals.add(_proposal(operation=ProposalOperation.ADD_LINK, content="[[Related Concept]]"))

    service.apply("proposal_1")

    written = (vault_root / "concept_1.md").read_text(encoding="utf-8")
    assert written == "# My notes\nSome text.\n[[Related Concept]]\n"


def test_apply_raises_when_proposal_not_found(tmp_path: Path) -> None:
    service, _, _, _engine_instance = _service(tmp_path)

    with pytest.raises(ProposalNotFoundError):
        service.apply("missing_proposal")


def test_apply_raises_when_proposal_not_approved(tmp_path: Path) -> None:
    service, proposals, _, _engine_instance = _service(tmp_path)
    proposals.add(_proposal(status=ProposalStatus.PENDING))

    with pytest.raises(ProposalNotApprovedError):
        service.apply("proposal_1")


def test_apply_marks_conflicted_when_file_changed_externally_since_indexing(
    tmp_path: Path,
) -> None:
    service, proposals, vault_root, engine = _service(tmp_path)
    (vault_root / "concept_1.md").write_text("externally edited\n", encoding="utf-8")
    proposals.add(
        _proposal(
            operation=ProposalOperation.REPLACE_MANAGED_SECTION,
            section="SUMMARY",
            content="New summary.",
        )
    )
    # index a stale hash for the path, simulating an external edit since last indexed
    with DbSession(engine) as db:
        db.add(
            VaultFileModel(
                path="concept_1.md",
                file_type="markdown",
                content_hash="stale-hash-does-not-match",
                modified_at=NOW.isoformat(),
                indexed_at=NOW.isoformat(),
                metadata_json="{}",
                missing=False,
            )
        )
        db.commit()

    result = service.apply("proposal_1")

    assert result.status == ProposalStatus.CONFLICTED
    assert (vault_root / "concept_1.md").read_text(encoding="utf-8") == "externally edited\n"
