from pathlib import Path

import pytest

from app.obsidian.conflict_detection import VaultConflictError, assert_no_conflict
from app.obsidian.vault_index import VaultIndexer
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine


def _setup(tmp_path: Path):  # type: ignore[no-untyped-def]
    vault = tmp_path / "vault"
    vault.mkdir()
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    resolver = VaultResolver(str(vault))
    return vault, engine, resolver


def test_no_conflict_when_file_never_indexed(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)
    (vault / "note.md").write_text("content")

    assert_no_conflict(engine, resolver, "note.md")  # must not raise


def test_no_conflict_when_unchanged_since_index(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)
    (vault / "note.md").write_text("content")
    VaultIndexer(engine, resolver).reindex()

    assert_no_conflict(engine, resolver, "note.md")  # must not raise


def test_conflict_when_file_changed_externally_since_index(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)
    note = vault / "note.md"
    note.write_text("original")
    VaultIndexer(engine, resolver).reindex()

    note.write_text("changed by someone else")

    with pytest.raises(VaultConflictError):
        assert_no_conflict(engine, resolver, "note.md")


def test_conflict_when_indexed_file_was_deleted(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)
    note = vault / "note.md"
    note.write_text("content")
    VaultIndexer(engine, resolver).reindex()

    note.unlink()

    with pytest.raises(VaultConflictError):
        assert_no_conflict(engine, resolver, "note.md")


def test_conflict_error_carries_the_path() -> None:
    error = VaultConflictError("Concepts/note.md")
    assert error.path == "Concepts/note.md"


def test_reindexing_after_external_change_clears_the_conflict(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)
    note = vault / "note.md"
    note.write_text("original")
    indexer = VaultIndexer(engine, resolver)
    indexer.reindex()

    note.write_text("changed externally")
    indexer.reindex()  # re-syncs the index to the new on-disk content

    assert_no_conflict(engine, resolver, "note.md")  # must not raise now
