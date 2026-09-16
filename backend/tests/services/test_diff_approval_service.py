from datetime import UTC, datetime

import pytest

from app.domain.enums import ProposalOperation
from app.obsidian.change_proposal import ChangeProposal, ProposalStatus
from app.services.diff_approval_service import (
    DiffApprovalService,
    InvalidProposalStatusError,
    ProposalNotFoundError,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeChangeProposalRepository:
    def __init__(self, proposals: list[ChangeProposal] | None = None) -> None:
        self._by_id = {p.id: p for p in (proposals or [])}

    def add(self, proposal: ChangeProposal) -> None:
        self._by_id[proposal.id] = proposal

    def get(self, proposal_id: str) -> ChangeProposal | None:
        return self._by_id.get(proposal_id)

    def list_by_status(self, status: ProposalStatus) -> list[ChangeProposal]:
        return [p for p in self._by_id.values() if p.status == status]

    def update_status(
        self, proposal_id: str, status: ProposalStatus, error: str | None = None
    ) -> None:
        proposal = self._by_id[proposal_id]
        self._by_id[proposal_id] = proposal.model_copy(update={"status": status, "error": error})


def _proposal(**overrides: object) -> ChangeProposal:
    defaults: dict[str, object] = dict(
        id="proposal_1",
        path="concept_1.md",
        operation=ProposalOperation.REPLACE_MANAGED_SECTION,
        section="SUMMARY",
        content="Updated summary.",
        status=ProposalStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return ChangeProposal(**defaults)  # type: ignore[arg-type]


def test_approve_transitions_pending_to_approved() -> None:
    proposals = FakeChangeProposalRepository([_proposal()])
    service = DiffApprovalService(proposals)

    result = service.approve("proposal_1")

    assert result.status == ProposalStatus.APPROVED
    assert proposals.get("proposal_1").status == ProposalStatus.APPROVED  # type: ignore[union-attr]


def test_reject_transitions_pending_to_rejected() -> None:
    proposals = FakeChangeProposalRepository([_proposal()])
    service = DiffApprovalService(proposals)

    result = service.reject("proposal_1")

    assert result.status == ProposalStatus.REJECTED


def test_approve_raises_when_proposal_not_found() -> None:
    service = DiffApprovalService(FakeChangeProposalRepository([]))

    with pytest.raises(ProposalNotFoundError):
        service.approve("missing_proposal")


def test_reject_raises_when_proposal_not_found() -> None:
    service = DiffApprovalService(FakeChangeProposalRepository([]))

    with pytest.raises(ProposalNotFoundError):
        service.reject("missing_proposal")


@pytest.mark.parametrize(
    "status",
    [
        ProposalStatus.APPROVED,
        ProposalStatus.REJECTED,
        ProposalStatus.APPLIED,
        ProposalStatus.CONFLICTED,
        ProposalStatus.FAILED,
    ],
)
def test_approve_raises_when_proposal_is_not_pending(status: ProposalStatus) -> None:
    proposals = FakeChangeProposalRepository([_proposal(status=status)])
    service = DiffApprovalService(proposals)

    with pytest.raises(InvalidProposalStatusError):
        service.approve("proposal_1")


def test_reject_raises_when_proposal_is_not_pending() -> None:
    proposals = FakeChangeProposalRepository([_proposal(status=ProposalStatus.APPROVED)])
    service = DiffApprovalService(proposals)

    with pytest.raises(InvalidProposalStatusError):
        service.reject("proposal_1")
