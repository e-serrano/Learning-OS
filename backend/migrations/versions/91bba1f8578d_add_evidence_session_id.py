"""add evidence session_id

Fixes a gap found while implementing T035: DOMAIN_MODEL.md #6 declares
session_id on the Evidence entity, but the evidence table (added in
fd57ee07b3b9) was missing it. Uses batch mode because SQLite cannot
ALTER a table to add a foreign key constraint directly.

Revision ID: 91bba1f8578d
Revises: 570ee5d78516
Create Date: 2026-09-15 12:41:39.219927

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "91bba1f8578d"
down_revision: str | None = "570ee5d78516"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table("evidence") as batch_op:
        batch_op.add_column(sa.Column("session_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_evidence_session_id_sessions", "sessions", ["session_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("evidence") as batch_op:
        batch_op.drop_constraint("fk_evidence_session_id_sessions", type_="foreignkey")
        batch_op.drop_column("session_id")
