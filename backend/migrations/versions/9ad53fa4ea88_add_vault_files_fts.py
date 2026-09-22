"""add vault files fts

docs/TASKS.md T127: full-text search over vault Markdown content.
`vault_files_fts` is a SQLite FTS5 virtual table, not something Alembic's
autogenerate or SQLAlchemy's declarative models can express -- raw DDL,
reusing the exact same SQL string `app/persistence/models/vault_search.py`
also runs after `Base.metadata.create_all()` in every test, so production
and tests never drift apart on the schema.

Revision ID: 9ad53fa4ea88
Revises: 82877dc3cd7c
Create Date: 2026-09-22 08:52:25.908640

"""

from alembic import op

from app.persistence.models.vault_search import (
    VAULT_SEARCH_FTS_CREATE_SQL,
    VAULT_SEARCH_FTS_DROP_SQL,
)

# revision identifiers, used by Alembic.
revision: str = "9ad53fa4ea88"
down_revision: str | None = "82877dc3cd7c"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(VAULT_SEARCH_FTS_CREATE_SQL)


def downgrade() -> None:
    op.execute(VAULT_SEARCH_FTS_DROP_SQL)
