"""add vault_files managed_id metadata missing

Fixes a gap found while implementing T042: its own acceptance criteria
name managed_id/metadata/missing on vault_files, but the table (added in
fd57ee07b3b9) had none of them. managed_id links a scanned file to its
frontmatter id (docs/OBSIDIAN_SCHEMA.md #3); missing supports the
deletion policy in docs/OBSIDIAN_SCHEMA.md #16.

Revision ID: 017d17b1666e
Revises: 91bba1f8578d
Create Date: 2026-09-15 14:48:59.250581

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "017d17b1666e"
down_revision: str | None = "91bba1f8578d"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("vault_files", sa.Column("managed_id", sa.String(), nullable=True))
    op.add_column(
        "vault_files",
        sa.Column("metadata_json", sa.String(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "vault_files",
        sa.Column("missing", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("vault_files", "missing")
    op.drop_column("vault_files", "metadata_json")
    op.drop_column("vault_files", "managed_id")
