from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class AIRunModel(Base):
    """Do not store raw prompts/responses here by default (docs/DATABASE_SCHEMA.md)."""

    __tablename__ = "ai_runs"

    id: Mapped[str] = mapped_column(primary_key=True)
    session_id: Mapped[str | None]
    role: Mapped[str]
    provider: Mapped[str]
    model: Mapped[str]
    prompt_version: Mapped[str]
    input_hash: Mapped[str | None]
    output_schema: Mapped[str | None]
    latency_ms: Mapped[int | None]
    success: Mapped[bool]
    error_type: Mapped[str | None]
    created_at: Mapped[str]
