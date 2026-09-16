"""add roadmaps table

Fixes a gap found while implementing T068: docs/DATABASE_SCHEMA.md never
listed a roadmaps table, despite docs/DOMAIN_MODEL.md #16 documenting
the Roadmap entity (id, goal_id, version, status). The graph itself
(nodes/edges) lives in goal_concepts and concept_relations, already
added by the initial schema -- this table is only the versioned
active/superseded marker for a goal's roadmap lifecycle.

Revision ID: 3c9a2ac5a47d
Revises: b9c38d0c7cf0
Create Date: 2026-09-16 12:31:20.652958

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c9a2ac5a47d"
down_revision: str | None = "b9c38d0c7cf0"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "roadmaps",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("goal_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_roadmaps_goal_version", "roadmaps", ["goal_id", "version"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_roadmaps_goal_version", table_name="roadmaps")
    op.drop_table("roadmaps")
