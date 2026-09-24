import subprocess
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
from app.services.vault_git_service import VaultGitService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _init_git_repo(path: Path) -> None:
    """Real `git init`, not a fake/mock -- a git failure that only ever
    shows up against real git behavior (e.g. missing committer identity)
    is exactly the kind of thing a mock would hide."""
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        capture_output=True,
        check=True,
    )


def _git_log(path: Path) -> str:
    result = subprocess.run(
        ["git", "log", "--oneline"], cwd=path, capture_output=True, text=True, check=True
    )
    return result.stdout


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


def test_apply_marks_failed_when_semantic_verification_fails(tmp_path: Path) -> None:
    """Malformed YAML frontmatter content is accepted by ProposalValidator
    (T081 doesn't parse YAML) but write_verification (T084) catches it
    after the write lands -- a real, reachable failure path, not a
    contrived one."""
    service, proposals, vault_root, _engine_instance = _service(tmp_path)
    proposals.add(
        _proposal(
            operation=ProposalOperation.UPDATE_FRONTMATTER,
            content="status: [unterminated",
        )
    )

    result = service.apply("proposal_1")

    assert result.status == ProposalStatus.FAILED
    assert result.error is not None and "failed to parse" in result.error
    # the write itself still landed -- verification is a check, not a rollback
    assert (vault_root / "concept_1.md").exists()


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


def test_apply_commits_the_written_file_when_the_vault_is_a_git_repo(tmp_path: Path) -> None:
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    _init_git_repo(vault_root)
    engine = _engine(tmp_path)
    proposals = ChangeProposalRepository(engine)
    vault = VaultResolver(str(vault_root))
    service = ApplyChangeService(engine, proposals, vault, git=VaultGitService(vault))
    proposals.add(_proposal())

    result = service.apply("proposal_1")

    assert result.status == ProposalStatus.APPLIED
    log = _git_log(vault_root)
    assert "create_file concept_1.md" in log


def test_apply_never_fails_when_the_vault_is_not_a_git_repo(tmp_path: Path) -> None:
    """A `VaultGitService` configured (auto-commit turned on) against a
    vault that just isn't a git repo must degrade to a no-op, never fail
    the apply that already succeeded (docs/TASKS.md T138: best-effort)."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()  # deliberately not a git repo
    engine = _engine(tmp_path)
    proposals = ChangeProposalRepository(engine)
    vault = VaultResolver(str(vault_root))
    service = ApplyChangeService(engine, proposals, vault, git=VaultGitService(vault))
    proposals.add(_proposal())

    result = service.apply("proposal_1")

    assert result.status == ProposalStatus.APPLIED
    assert (vault_root / "concept_1.md").exists()


def test_apply_does_not_sweep_unrelated_dirty_changes_into_the_commit(tmp_path: Path) -> None:
    """docs/AGENTS.md #22: 'never overwrite unrelated dirty changes' --
    an unrelated file the user was mid-editing in the same vault repo
    must stay exactly as dirty/untracked as it was before our commit."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    _init_git_repo(vault_root)
    (vault_root / "unrelated.md").write_text("work in progress\n", encoding="utf-8")
    engine = _engine(tmp_path)
    proposals = ChangeProposalRepository(engine)
    vault = VaultResolver(str(vault_root))
    service = ApplyChangeService(engine, proposals, vault, git=VaultGitService(vault))
    proposals.add(_proposal())

    service.apply("proposal_1")

    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=vault_root, capture_output=True, text=True, check=True
    ).stdout
    assert "?? unrelated.md" in status  # still untracked -- never staged, never committed
