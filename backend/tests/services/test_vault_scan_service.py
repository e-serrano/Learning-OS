from pathlib import Path

from sqlalchemy import Engine

from app.obsidian.vault_resolver import VaultResolver
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.services.vault_scan_service import VaultScanService


def _service(tmp_path: Path, vault_dir: Path) -> tuple[VaultScanService, Engine]:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    resolver = VaultResolver(str(vault_dir))
    return VaultScanService(engine, resolver), engine


def test_scan_empty_vault(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    service, _ = _service(tmp_path, vault)

    result = service.scan()

    assert result.files_scanned == 0
    assert result.managed_files == 0
    assert result.changed_files == 0
    assert result.errors == []


def test_first_scan_counts_every_file_as_changed(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "note.md").write_text("# Note\n")
    (vault / "concept.md").write_text(
        "---\nid: concept_x\ntype: concept\nmanaged_by: learning_os\n---\nBody\n"
    )
    service, _ = _service(tmp_path, vault)

    result = service.scan()

    assert result.files_scanned == 2
    assert result.managed_files == 1
    assert result.changed_files == 2


def test_rescan_with_no_changes_reports_zero_changed(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "note.md").write_text("# Note\n")
    service, _ = _service(tmp_path, vault)
    service.scan()

    result = service.scan()

    assert result.files_scanned == 1
    assert result.changed_files == 0


def test_rescan_after_editing_a_file_counts_only_that_file_as_changed(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "a.md").write_text("A\n")
    (vault / "b.md").write_text("B\n")
    service, _ = _service(tmp_path, vault)
    service.scan()

    (vault / "a.md").write_text("A changed\n")
    result = service.scan()

    assert result.files_scanned == 2
    assert result.changed_files == 1


def test_rescan_after_adding_a_new_file_counts_only_the_new_file(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "a.md").write_text("A\n")
    service, _ = _service(tmp_path, vault)
    service.scan()

    (vault / "b.md").write_text("B\n")
    result = service.scan()

    assert result.files_scanned == 2
    assert result.changed_files == 1
