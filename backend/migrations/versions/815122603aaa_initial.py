"""initial

Empty baseline revision that proves the Alembic tooling runs against an
empty database and establishes version tracking. Real tables land in
later revisions (T033 domain models, T034 config tables).

Revision ID: 815122603aaa
Revises:
Create Date: 2026-09-15 09:56:53.810265

"""

revision: str = "815122603aaa"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
