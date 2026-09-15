from pathlib import Path

import pytest
from sqlalchemy.orm import Session as DbSession

from app.obsidian.atomic_writer import write_note
from app.obsidian.conflict_detection import VaultConflictError
from app.obsidian.vault_index import VaultIndexer
from app.obsidian.vault_resolver import VaultPathTraversalError, VaultResolver
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import VaultFileModel


def _setup(tmp_path: Path):  # type: ignore[no-untyped-def]
    vault = tmp_path / "vault"
    vault.mkdir()
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    resolver = VaultResolver(str(vault))
    return vault, engine, resolver


def test_write_creates_new_file(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)

    write_note(engine, resolver, "note.md", "# Hello\n")

    assert (vault / "note.md").read_text() == "# Hello\n"


def test_write_creates_parent_directories(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)

    write_note(engine, resolver, "Concepts/note.md", "content")

    assert (vault / "Concepts" / "note.md").read_text() == "content"


def test_write_updates_vault_index(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)

    new_hash = write_note(engine, resolver, "note.md", "content")

    with DbSession(engine) as db:
        row = db.get(VaultFileModel, "note.md")
        assert row is not None
        assert row.content_hash == new_hash
        assert row.missing is False


def test_write_leaves_no_temp_files_behind(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)

    write_note(engine, resolver, "note.md", "content")

    assert list(vault.iterdir()) == [vault / "note.md"]


def test_write_overwrites_existing_content(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)
    write_note(engine, resolver, "note.md", "v1")

    write_note(engine, resolver, "note.md", "v2")

    assert (vault / "note.md").read_text() == "v2"


def test_write_blocks_path_traversal(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)

    with pytest.raises(VaultPathTraversalError):
        write_note(engine, resolver, "../outside.md", "content")


def test_write_rejects_when_file_changed_externally_since_last_index(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)
    note = vault / "note.md"
    note.write_text("original")
    VaultIndexer(engine, resolver).reindex()

    note.write_text("changed by the user in Obsidian")

    with pytest.raises(VaultConflictError):
        write_note(engine, resolver, "note.md", "learning os wants to overwrite")

    # the external edit must survive
    assert note.read_text() == "changed by the user in Obsidian"


def test_write_succeeds_after_reindexing_past_a_conflict(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)
    note = vault / "note.md"
    note.write_text("original")
    indexer = VaultIndexer(engine, resolver)
    indexer.reindex()

    note.write_text("changed externally")
    indexer.reindex()  # acknowledges the external change

    write_note(engine, resolver, "note.md", "learning os update")
    assert note.read_text() == "learning os update"


def test_write_to_new_untracked_path_has_no_conflict(tmp_path: Path) -> None:
    vault, engine, resolver = _setup(tmp_path)

    write_note(engine, resolver, "brand-new.md", "content")  # must not raise

    assert (vault / "brand-new.md").read_text() == "content"
