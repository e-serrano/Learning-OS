"""add projects table

Fixes a gap found while implementing T092: docs/DATABASE_SCHEMA.md never
listed a projects table, despite docs/DOMAIN_MODEL.md #14 documenting
the Project entity. project_concepts mirrors exercise_concepts/
goal_concepts -- concept_ids (added to the Project entity in T092, it
had no way to record which concepts a project targets) live in a join
table, not inline JSON.

Revision ID: 82877dc3cd7c
Revises: 3c9a2ac5a47d
Create Date: 2026-09-17 10:49:10.255229

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "82877dc3cd7c"
down_revision: str | None = "3c9a2ac5a47d"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "projects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("goal_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("objective", sa.String(), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("success_criteria_json", sa.String(), nullable=False),
        sa.Column("artifact_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "project_concepts",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("concept_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("project_id", "concept_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("project_concepts")
    op.drop_table("projects")
