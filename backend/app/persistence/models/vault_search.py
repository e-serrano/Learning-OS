"""Full-text search index over vault Markdown content (docs/TASKS.md
T127, docs/ROADMAP.md Phase 10 "Advanced retrieval").

Not a `DeclarativeBase` model: SQLite FTS5 virtual tables aren't
expressible as an ORM-mapped table (docs/DATABASE_SCHEMA.md has no
FTS5 mapping support in SQLAlchemy), so this is raw DDL instead. It
still needs to exist wherever `vault_files` does -- both the real app
(via an Alembic migration reusing `VAULT_SEARCH_FTS_CREATE_SQL`) and
every test that builds its schema with `Base.metadata.create_all()`
(via the `after_create`/`after_drop` listeners registered below, which
fire automatically once this module is imported -- see
`models/__init__.py`).

A standalone (not external-content) FTS5 table: `reindex()` fully
deletes-then-reinserts a file's row on every scan, since it already
re-reads every file's content anyway (`vault_index.py`). This is
simpler and more robust than SQLite's external-content sync triggers
for a table that's rebuilt from a full scan on every use, not
incrementally maintained.
"""

from sqlalchemy import event, text

from app.persistence.base import Base

VAULT_SEARCH_FTS_TABLE = "vault_files_fts"

VAULT_SEARCH_FTS_CREATE_SQL = f"""
CREATE VIRTUAL TABLE IF NOT EXISTS {VAULT_SEARCH_FTS_TABLE} USING fts5(
    path UNINDEXED,
    title,
    body,
    tokenize = 'porter unicode61'
)
"""

VAULT_SEARCH_FTS_DROP_SQL = f"DROP TABLE IF EXISTS {VAULT_SEARCH_FTS_TABLE}"


@event.listens_for(Base.metadata, "after_create")
def _create_vault_search_fts(target: object, connection: object, **kw: object) -> None:
    connection.execute(text(VAULT_SEARCH_FTS_CREATE_SQL))  # type: ignore[attr-defined]


@event.listens_for(Base.metadata, "after_drop")
def _drop_vault_search_fts(target: object, connection: object, **kw: object) -> None:
    connection.execute(text(VAULT_SEARCH_FTS_DROP_SQL))  # type: ignore[attr-defined]
