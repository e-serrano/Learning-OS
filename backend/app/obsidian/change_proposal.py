from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.domain.enums import ProposalOperation
from app.persistence.models import ChangeProposalModel

__all__ = [
    "ProposalOperation",  # re-exported: this module is its established home for callers
    "ProposalStatus",
    "ChangeProposal",
    "ChangeProposalRepository",
]


class ProposalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    CONFLICTED = "conflicted"
    FAILED = "failed"


class ChangeProposal(BaseModel):
    """A pending Obsidian write, requiring user approval before it lands
    on disk -- see docs/SPECS.md #16 and docs/AI_CONTRACTS.md #9.

    Applying an approved proposal (writing it, handling conflicts) is a
    later concern (T083); this only models and persists the proposal.
    """

    id: str
    path: str
    operation: ProposalOperation
    section: str | None = None
    content: str
    status: ProposalStatus = ProposalStatus.PENDING
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    applied_at: datetime | None = None


def _to_model(proposal: ChangeProposal) -> ChangeProposalModel:
    return ChangeProposalModel(
        id=proposal.id,
        path=proposal.path,
        operation=proposal.operation.value,
        section=proposal.section,
        content=proposal.content,
        status=proposal.status.value,
        error=proposal.error,
        created_at=proposal.created_at.isoformat(),
        updated_at=proposal.updated_at.isoformat(),
        applied_at=proposal.applied_at.isoformat() if proposal.applied_at else None,
    )


def _to_entity(model: ChangeProposalModel) -> ChangeProposal:
    return ChangeProposal(
        id=model.id,
        path=model.path,
        operation=model.operation,  # type: ignore[arg-type]
        section=model.section,
        content=model.content,
        status=model.status,  # type: ignore[arg-type]
        error=model.error,
        created_at=datetime.fromisoformat(model.created_at),
        updated_at=datetime.fromisoformat(model.updated_at),
        applied_at=datetime.fromisoformat(model.applied_at) if model.applied_at else None,
    )


class ChangeProposalRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, proposal: ChangeProposal) -> None:
        with DbSession(self._engine) as db:
            db.add(_to_model(proposal))
            db.commit()

    def get(self, proposal_id: str) -> ChangeProposal | None:
        with DbSession(self._engine) as db:
            model = db.get(ChangeProposalModel, proposal_id)
            return _to_entity(model) if model is not None else None

    def list_by_status(self, status: ProposalStatus) -> list[ChangeProposal]:
        with DbSession(self._engine) as db:
            stmt = select(ChangeProposalModel).where(ChangeProposalModel.status == status.value)
            return [_to_entity(m) for m in db.scalars(stmt)]

    def update_status(
        self, proposal_id: str, status: ProposalStatus, error: str | None = None
    ) -> None:
        with DbSession(self._engine) as db:
            model = db.get(ChangeProposalModel, proposal_id)
            if model is None:
                raise ValueError(f"No change proposal with id {proposal_id!r}")
            model.status = status.value
            model.error = error
            model.updated_at = datetime.now(UTC).isoformat()
            if status == ProposalStatus.APPLIED:
                model.applied_at = model.updated_at
            db.commit()
