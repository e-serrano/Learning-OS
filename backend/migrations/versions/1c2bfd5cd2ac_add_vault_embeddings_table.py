"""add vault embeddings table

docs/TASKS.md T128: one embedding vector per indexed vault file, kept
in `vault_embeddings`.

Note for future migrations: autogenerate against this revision's parent
(`9ad53fa4ea88`, `vault_files_fts`) also proposes dropping and
recreating FTS5's own internal shadow tables (`vault_files_fts_data`,
`_idx`, `_config`, `_content`, `_docsize`) -- those aren't part of
`Base.metadata` (SQLite creates them automatically for any FTS5 virtual
table), so autogenerate sees them as unexplained and wants to remove
them. That noise was stripped from this migration by hand; only the
real, intended change (`vault_embeddings`) is here.

Revision ID: 1c2bfd5cd2ac
Revises: 9ad53fa4ea88
Create Date: 2026-09-22 11:17:57.534131

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1c2bfd5cd2ac"
down_revision: str | None = "9ad53fa4ea88"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "vault_embeddings",
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("dims", sa.Integer(), nullable=False),
        sa.Column("vector_json", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("path"),
    )


def downgrade() -> None:
    op.drop_table("vault_embeddings")
