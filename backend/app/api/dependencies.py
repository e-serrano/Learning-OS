import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import Engine

from app.ai.orchestrator import AIOrchestrator
from app.ai.provider_factory import (
    MissingBaseUrlError,
    MissingCredentialError,
    NoDefaultProviderError,
    build_default_provider,
)
from app.config import ConfigStore, CredentialStore, Settings
from app.obsidian.change_proposal import ChangeProposalRepository
from app.obsidian.vault_resolver import VaultResolver, VaultUnavailableError
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories.concept import SqlConceptRepository
from app.persistence.repositories.concept_relation import SqlConceptRelationRepository
from app.persistence.repositories.goal import SqlGoalRepository
from app.persistence.repositories.roadmap import SqlRoadmapRepository
from app.services.apply_change_service import ApplyChangeService
from app.services.diff_approval_service import DiffApprovalService
from app.services.goal_service import GoalApplicationService
from app.services.knowledge_explorer_service import KnowledgeExplorerService
from app.services.planner_service import PlannerService
from app.services.roadmap_generation_service import RoadmapGenerationService
from app.services.roadmap_service import RoadmapService
from app.services.vault_scan_service import VaultScanService


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidIdGenerator:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_config_store() -> ConfigStore:
    return ConfigStore(get_settings().db_path)


def get_credential_store() -> CredentialStore:
    return CredentialStore()


@lru_cache
def get_engine() -> Engine:
    return create_sqlite_engine(get_settings().db_path)


def get_clock() -> SystemClock:
    return SystemClock()


def get_id_generator() -> UuidIdGenerator:
    return UuidIdGenerator()


def get_goal_repository() -> SqlGoalRepository:
    return SqlGoalRepository(get_engine())


def get_goal_service() -> GoalApplicationService:
    return GoalApplicationService(get_goal_repository(), get_clock(), get_id_generator())


def get_vault_resolver(store: Annotated[ConfigStore, Depends(get_config_store)]) -> VaultResolver:
    """Raises HTTPException directly (rather than a plain error) -- FastAPI
    resolves dependencies before the route body runs, so a route-level
    try/except can never see an exception raised here (docs/TASKS.md T097).

    Takes `store` through `Depends()` rather than calling
    `get_config_store()` directly so `app.dependency_overrides` can
    actually reach it in tests -- a plain internal call bypasses
    FastAPI's override resolution entirely."""
    config = store.load()
    if config.vault_path is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VAULT_UNAVAILABLE",
                    "message": "Vault is not configured",
                    "details": {},
                }
            },
        )
    try:
        return VaultResolver(config.vault_path)
    except VaultUnavailableError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VAULT_UNAVAILABLE", "message": str(exc), "details": {}}},
        ) from exc


def get_change_proposal_repository() -> ChangeProposalRepository:
    return ChangeProposalRepository(get_engine())


def get_vault_scan_service(
    vault: Annotated[VaultResolver, Depends(get_vault_resolver)],
) -> VaultScanService:
    return VaultScanService(get_engine(), vault)


def get_apply_change_service(
    vault: Annotated[VaultResolver, Depends(get_vault_resolver)],
) -> ApplyChangeService:
    return ApplyChangeService(get_engine(), get_change_proposal_repository(), vault)


def get_diff_approval_service() -> DiffApprovalService:
    return DiffApprovalService(get_change_proposal_repository())


def get_concept_repository() -> SqlConceptRepository:
    return SqlConceptRepository(get_engine())


def get_concept_relation_repository() -> SqlConceptRelationRepository:
    return SqlConceptRelationRepository(get_engine())


def get_knowledge_explorer_service() -> KnowledgeExplorerService:
    return KnowledgeExplorerService(
        get_goal_repository(), get_concept_repository(), get_concept_relation_repository()
    )


def get_ai_orchestrator(
    store: Annotated[ConfigStore, Depends(get_config_store)],
) -> AIOrchestrator:
    """Builds the orchestrator around the user's configured default AI
    provider (docs/TASKS.md T101 -- the first route to call the AI
    orchestrator over HTTP). Raises HTTPException directly for the same
    reason `get_vault_resolver` does (docs/TASKS.md T097)."""
    config = store.load()
    try:
        provider, provider_name, model = build_default_provider(
            config.ai_providers, get_credential_store()
        )
    except (NoDefaultProviderError, MissingCredentialError, MissingBaseUrlError) as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "AI_UNAVAILABLE", "message": str(exc), "details": {}}},
        ) from exc
    return AIOrchestrator(get_engine(), provider, provider_name=provider_name, model=model)


def get_roadmap_repository() -> SqlRoadmapRepository:
    return SqlRoadmapRepository(get_engine())


def get_planner_service(
    orchestrator: Annotated[AIOrchestrator, Depends(get_ai_orchestrator)],
) -> PlannerService:
    return PlannerService(get_goal_repository(), get_concept_repository(), orchestrator)


def get_roadmap_service() -> RoadmapService:
    return RoadmapService(
        goals=get_goal_repository(),
        concepts=get_concept_repository(),
        concept_relations=get_concept_relation_repository(),
        roadmaps=get_roadmap_repository(),
        clock=get_clock(),
        ids=get_id_generator(),
    )


def get_roadmap_generation_service(
    planner: Annotated[PlannerService, Depends(get_planner_service)],
    roadmaps: Annotated[RoadmapService, Depends(get_roadmap_service)],
) -> RoadmapGenerationService:
    return RoadmapGenerationService(planner, roadmaps)
