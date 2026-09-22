from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session as DbSession

from app.obsidian.vault_index import VaultIndexer
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import VAULT_SEARCH_FTS_TABLE, VaultFileModel


def _make_indexer(tmp_path: Path, vault_dir: Path):  # type: ignore[no-untyped-def]
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    resolver = VaultResolver(str(vault_dir))
    return VaultIndexer(engine, resolver), engine


def _match_sql(columns: str, term: str) -> str:
    return (
        f"SELECT {columns} FROM {VAULT_SEARCH_FTS_TABLE} "
        f"WHERE {VAULT_SEARCH_FTS_TABLE} MATCH '{term}'"
    )


def test_reindex_empty_vault_returns_no_entries(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    indexer, _ = _make_indexer(tmp_path, vault)

    assert indexer.reindex() == []


def test_reindex_persists_unmanaged_file(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "note.md").write_text("# Just a note\n")
    indexer, engine = _make_indexer(tmp_path, vault)

    entries = indexer.reindex()

    assert len(entries) == 1
    assert entries[0].path == "note.md"
    assert entries[0].managed_id is None
    assert entries[0].missing is False

    with DbSession(engine) as db:
        row = db.get(VaultFileModel, "note.md")
        assert row is not None
        assert row.file_type == "markdown"
        assert row.missing is False


def test_reindex_extracts_managed_id_from_frontmatter(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "concept.md").write_text(
        "---\nid: concept_sql_window_functions\ntype: concept\nmanaged_by: learning_os\n---\nBody\n"
    )
    indexer, _ = _make_indexer(tmp_path, vault)

    entries = indexer.reindex()

    assert entries[0].managed_id == "concept_sql_window_functions"
    assert entries[0].metadata["type"] == "concept"


def test_reindex_ignores_id_without_managed_by_marker(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "note.md").write_text("---\nid: not_ours\n---\nBody\n")
    indexer, _ = _make_indexer(tmp_path, vault)

    entries = indexer.reindex()

    assert entries[0].managed_id is None


def test_reindex_updates_hash_when_content_changes(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "note.md"
    note.write_text("v1")
    indexer, _ = _make_indexer(tmp_path, vault)
    first = indexer.reindex()[0].content_hash

    note.write_text("v2")
    second = indexer.reindex()[0].content_hash

    assert first != second


def test_reindex_marks_deleted_file_as_missing_not_deleted(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "note.md"
    note.write_text("content")
    indexer, engine = _make_indexer(tmp_path, vault)
    indexer.reindex()

    note.unlink()
    indexer.reindex()

    with DbSession(engine) as db:
        row = db.get(VaultFileModel, "note.md")
        assert row is not None  # never deleted
        assert row.missing is True


def test_reindex_unmark_missing_when_file_reappears(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "note.md"
    note.write_text("content")
    indexer, engine = _make_indexer(tmp_path, vault)
    indexer.reindex()

    note.unlink()
    indexer.reindex()
    note.write_text("content again")
    indexer.reindex()

    with DbSession(engine) as db:
        row = db.get(VaultFileModel, "note.md")
        assert row is not None
        assert row.missing is False


def test_reindex_never_writes_to_vault_files(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "note.md").write_text("content")
    indexer, _ = _make_indexer(tmp_path, vault)

    before = (vault / "note.md").read_text()
    indexer.reindex()
    after = (vault / "note.md").read_text()

    assert before == after


def test_reindex_populates_the_fts_index(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "window_functions.md").write_text(
        "# Window Functions\n\nUses OVER() to rank rows across partitions.\n"
    )
    indexer, engine = _make_indexer(tmp_path, vault)

    indexer.reindex()

    with engine.connect() as conn:
        rows = list(conn.execute(text(_match_sql("path, title", "partitions"))))
    assert rows == [("window_functions.md", "Window Functions")]


def test_reindex_derives_title_from_frontmatter_over_heading(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "note.md").write_text("---\ntitle: Custom Title\n---\n# Different Heading\n\nBody.\n")
    indexer, engine = _make_indexer(tmp_path, vault)

    indexer.reindex()

    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT title FROM {VAULT_SEARCH_FTS_TABLE} WHERE path = 'note.md'")
        ).one()
    assert row.title == "Custom Title"


def test_reindex_derives_title_from_filename_when_no_frontmatter_or_heading(
    tmp_path: Path,
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "plain_note.md").write_text("Just body text, no heading.\n")
    indexer, engine = _make_indexer(tmp_path, vault)

    indexer.reindex()

    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT title FROM {VAULT_SEARCH_FTS_TABLE} WHERE path = 'plain_note.md'")
        ).one()
    assert row.title == "plain_note"


def test_reindex_updates_fts_content_when_file_changes(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "note.md"
    note.write_text("original wording")
    indexer, engine = _make_indexer(tmp_path, vault)
    indexer.reindex()

    note.write_text("updated wording")
    indexer.reindex()

    with engine.connect() as conn:
        rows = list(conn.execute(text(_match_sql("path", "original"))))
    assert rows == []


def test_reindex_removes_fts_entry_for_a_missing_file(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "note.md"
    note.write_text("unique searchable phrase")
    indexer, engine = _make_indexer(tmp_path, vault)
    indexer.reindex()

    note.unlink()
    indexer.reindex()

    with engine.connect() as conn:
        rows = list(conn.execute(text(_match_sql("path", "unique"))))
    assert rows == []


def test_reindex_indexes_multiple_files(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "a.md").write_text("A")
    (vault / "b.md").write_text("B")
    indexer, engine = _make_indexer(tmp_path, vault)

    indexer.reindex()

    with DbSession(engine) as db:
        rows = list(db.scalars(select(VaultFileModel)))
        assert {r.path for r in rows} == {"a.md", "b.md"}
