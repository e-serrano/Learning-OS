"""Vault routes (docs/TASKS.md T097, docs/API_SPEC.md #2).

`apply` performs `pending -> approved -> applied` in one call: the API
surface deliberately has no separate `/approve` route
(docs/services/diff_approval_service.py's own docstring), so this route
is where `DiffApprovalService.approve()` and `ApplyChangeService.apply()`
are chained together.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import (
    get_apply_change_service,
    get_change_proposal_repository,
    get_config_store,
    get_diff_approval_service,
    get_vault_scan_service,
)
from app.config.store import ConfigStore
from app.domain.enums import ProposalOperation
from app.obsidian.change_proposal import ChangeProposal, ChangeProposalRepository, ProposalStatus
from app.obsidian.onboarding_scan import scan_vault_readonly
from app.services.apply_change_service import ApplyChangeService
from app.services.diff_approval_service import (
    DiffApprovalService,
    InvalidProposalStatusError,
    ProposalNotFoundError,
)
from app.services.vault_scan_service import VaultReindexSummary, VaultScanService

router = APIRouter(prefix="/api/v1/vault", tags=["vault"])

ConfigStoreDep = Annotated[ConfigStore, Depends(get_config_store)]
ChangeProposalRepositoryDep = Annotated[
    ChangeProposalRepository, Depends(get_change_proposal_repository)
]
VaultScanServiceDep = Annotated[VaultScanService, Depends(get_vault_scan_service)]
ApplyChangeServiceDep = Annotated[ApplyChangeService, Depends(get_apply_change_service)]
DiffApprovalServiceDep = Annotated[DiffApprovalService, Depends(get_diff_approval_service)]


def _error(code: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": {}}},
    )


class ConfigureVaultRequest(BaseModel):
    path: str


class ConfigureVaultResponse(BaseModel):
    vault_path: str


class ChangeProposalResponse(BaseModel):
    id: str
    path: str
    operation: ProposalOperation
    section: str | None
    content: str
    status: ProposalStatus
    error: str | None
    created_at: datetime
    updated_at: datetime
    applied_at: datetime | None

    @classmethod
    def from_entity(cls, proposal: ChangeProposal) -> "ChangeProposalResponse":
        return cls(**proposal.model_dump())


class ChangeProposalListResponse(BaseModel):
    changes: list[ChangeProposalResponse]


@router.post("/configure", response_model=ConfigureVaultResponse)
def configure_vault(
    request: ConfigureVaultRequest, store: ConfigStoreDep
) -> ConfigureVaultResponse:
    scan = scan_vault_readonly(request.path)
    if not scan.exists or not scan.readable:
        raise _error(
            "VAULT_UNAVAILABLE",
            f"Vault path is not usable: {'; '.join(scan.errors) or 'unknown error'}",
            400,
        )

    config = store.load()
    config.vault_path = request.path
    store.save(config)
    return ConfigureVaultResponse(vault_path=request.path)


@router.post("/scan", response_model=VaultReindexSummary)
def scan_vault(service: VaultScanServiceDep) -> VaultReindexSummary:
    return service.scan()


@router.get("/changes", response_model=ChangeProposalListResponse)
def list_changes(repo: ChangeProposalRepositoryDep) -> ChangeProposalListResponse:
    pending = repo.list_by_status(ProposalStatus.PENDING)
    return ChangeProposalListResponse(
        changes=[ChangeProposalResponse.from_entity(p) for p in pending]
    )


@router.post("/changes/{change_id}/apply", response_model=ChangeProposalResponse)
def apply_change(
    change_id: str, approval: DiffApprovalServiceDep, applier: ApplyChangeServiceDep
) -> ChangeProposalResponse:
    try:
        approval.approve(change_id)
    except ProposalNotFoundError as exc:
        raise _error("NOT_FOUND", f"Change proposal '{change_id}' not found", 404) from exc
    except InvalidProposalStatusError as exc:
        raise _error("CONFLICT", str(exc), 409) from exc

    proposal = applier.apply(change_id)
    return ChangeProposalResponse.from_entity(proposal)


@router.post("/changes/{change_id}/reject", response_model=ChangeProposalResponse)
def reject_change(change_id: str, approval: DiffApprovalServiceDep) -> ChangeProposalResponse:
    try:
        proposal = approval.reject(change_id)
    except ProposalNotFoundError as exc:
        raise _error("NOT_FOUND", f"Change proposal '{change_id}' not found", 404) from exc
    except InvalidProposalStatusError as exc:
        raise _error("CONFLICT", str(exc), 409) from exc
    return ChangeProposalResponse.from_entity(proposal)
