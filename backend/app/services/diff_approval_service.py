"""Diff approval -- approve or reject a pending knowledge proposal
(docs/TASKS.md T082).

docs/API_SPEC.md #2 exposes `apply`/`reject` as HTTP routes with no
separate `/approve` route -- those routes are built in Phase 10
(T096-T108), not here. This service is the application-layer state
transition (`pending -> approved` / `pending -> rejected`) that a future
route handler calls; T083 (apply) only ever writes an `approved`
proposal, never a merely-pending one.
"""

from app.obsidian.change_proposal import ChangeProposal, ChangeProposalRepository, ProposalStatus


class ProposalNotFoundError(Exception):
    pass


class InvalidProposalStatusError(Exception):
    pass


class DiffApprovalService:
    def __init__(self, proposals: ChangeProposalRepository) -> None:
        self._proposals = proposals

    def approve(self, proposal_id: str) -> ChangeProposal:
        self._require_pending(proposal_id)
        self._proposals.update_status(proposal_id, ProposalStatus.APPROVED)
        return self._reload(proposal_id)

    def reject(self, proposal_id: str) -> ChangeProposal:
        self._require_pending(proposal_id)
        self._proposals.update_status(proposal_id, ProposalStatus.REJECTED)
        return self._reload(proposal_id)

    def _require_pending(self, proposal_id: str) -> ChangeProposal:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise ProposalNotFoundError(proposal_id)
        if proposal.status != ProposalStatus.PENDING:
            raise InvalidProposalStatusError(
                f"proposal {proposal_id} is {proposal.status.value}, not pending"
            )
        return proposal

    def _reload(self, proposal_id: str) -> ChangeProposal:
        proposal = self._proposals.get(proposal_id)
        assert proposal is not None  # just written; must exist
        return proposal
