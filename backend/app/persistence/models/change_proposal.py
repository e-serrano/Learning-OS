from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class ChangeProposalModel(Base):
    """An AI-curator-suggested Obsidian write, pending user approval.

    See docs/SPECS.md #16, docs/AI_CONTRACTS.md #9, docs/AGENTS.md #6.
    Added while implementing T046 -- absent from the original schema.
    """

    __tablename__ = "change_proposals"

    id: Mapped[str] = mapped_column(primary_key=True)
    path: Mapped[str]
    operation: Mapped[str]
    section: Mapped[str | None]
    content: Mapped[str]
    status: Mapped[str]
    error: Mapped[str | None]
    created_at: Mapped[str]
    updated_at: Mapped[str]
    applied_at: Mapped[str | None]
