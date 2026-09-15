from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.persistence.engine import create_sqlite_engine


def test_foreign_keys_are_enabled(tmp_path: Path) -> None:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys")).scalar()
    assert result == 1


def test_journal_mode_is_wal(tmp_path: Path) -> None:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA journal_mode")).scalar()
    assert result == "wal"


def test_busy_timeout_is_set(tmp_path: Path) -> None:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA busy_timeout")).scalar()
    assert result == 30000


def test_creates_parent_directory_if_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "dir" / "test.sqlite3"
    create_sqlite_engine(str(db_path))
    assert db_path.parent.exists()


def test_foreign_key_violation_is_rejected(tmp_path: Path) -> None:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE parent (id TEXT PRIMARY KEY)"))
        conn.execute(
            text(
                "CREATE TABLE child (id TEXT PRIMARY KEY, "
                "parent_id TEXT NOT NULL, FOREIGN KEY (parent_id) REFERENCES parent(id))"
            )
        )

    with engine.begin() as conn, pytest.raises(IntegrityError):
        conn.execute(text("INSERT INTO child (id, parent_id) VALUES ('c1', 'does-not-exist')"))
