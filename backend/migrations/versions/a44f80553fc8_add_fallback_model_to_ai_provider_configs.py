"""add fallback_model to ai_provider_configs

docs/TASKS.md T148, user request: a second model per provider config,
tried by RetryingProvider (app/ai/provider_factory.py) if the primary
model errors out or is rate-limited -- same provider/credential/base_url,
just a different model. Nullable: existing rows have no fallback
configured, matching RetryingProvider's own `fallback: AIProvider | None`
default of "no fallback" it already had before this column existed.

Revision ID: a44f80553fc8
Revises: 1c2bfd5cd2ac
Create Date: 2026-09-25 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a44f80553fc8"
down_revision: str | None = "1c2bfd5cd2ac"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("ai_provider_configs", sa.Column("fallback_model", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_provider_configs", "fallback_model")
