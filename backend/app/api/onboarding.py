from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.ai.adapters.ollama import list_ollama_models
from app.ai.capability_check import (
    DEFAULT_OLLAMA_BASE_URL,
    check_provider_capability,
    validate_provider_connection,
)
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.ai.provider_registry import ProviderId
from app.api.dependencies import get_config_store, get_credential_store
from app.api.errors import api_error
from app.config.credentials import CredentialStore, new_credential_ref
from app.config.models import AIProviderConfig, OnboardingStep
from app.config.store import ConfigStore
from app.obsidian.onboarding_scan import VaultScanResult, scan_vault_readonly
from app.onboarding.state_machine import next_step

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])

ConfigStoreDep = Annotated[ConfigStore, Depends(get_config_store)]
CredentialStoreDep = Annotated[CredentialStore, Depends(get_credential_store)]


def _advance_to(config_step: OnboardingStep, target: OnboardingStep) -> OnboardingStep:
    """Advance linearly, one validated step at a time, until `target` is reached."""
    step = config_step
    while step != target:
        nxt = next_step(step)
        if nxt is None:
            raise api_error("SESSION_STATE_ERROR", "Onboarding already complete", 409)
        step = nxt
    return step


class OnboardingStatusResponse(BaseModel):
    onboarding_step: OnboardingStep
    vault_path: str | None
    provider_id: str | None
    model: str | None
    language: str
    ai_providers: list[AIProviderConfig]


class VaultRequest(BaseModel):
    path: str


class VaultResponse(BaseModel):
    onboarding_step: OnboardingStep
    scan: VaultScanResult


class AIProviderRequest(BaseModel):
    provider_id: ProviderId
    model: str
    base_url: str | None = None
    fallback_model: str | None = None


class AIProviderResponse(BaseModel):
    onboarding_step: OnboardingStep


class ValidateRequest(BaseModel):
    credential: str | None = None


class ValidateResponse(BaseModel):
    onboarding_step: OnboardingStep
    ok: bool
    reason: str | None = None


class CompleteResponse(BaseModel):
    onboarding_step: OnboardingStep


class OllamaModelsResponse(BaseModel):
    models: list[str]


@router.get("/status", response_model=OnboardingStatusResponse)
def get_status(store: ConfigStoreDep) -> OnboardingStatusResponse:
    config = store.load()
    return OnboardingStatusResponse(
        onboarding_step=config.onboarding_step,
        vault_path=config.vault_path,
        provider_id=config.provider_id,
        model=config.model,
        language=config.language,
        ai_providers=config.ai_providers,
    )


@router.post("/vault", response_model=VaultResponse)
def configure_vault(request: VaultRequest, store: ConfigStoreDep) -> VaultResponse:
    config = store.load()
    scan = scan_vault_readonly(request.path)
    if not scan.exists or not scan.readable:
        raise api_error(
            "VAULT_UNAVAILABLE",
            f"Vault path is not usable: {'; '.join(scan.errors) or 'unknown error'}",
            400,
        )

    config.vault_path = request.path
    if config.onboarding_step != OnboardingStep.COMPLETE:
        config.onboarding_step = _advance_to(config.onboarding_step, OnboardingStep.VAULT_SCAN)

    store.save(config)
    return VaultResponse(onboarding_step=config.onboarding_step, scan=scan)


@router.post("/ai-provider", response_model=AIProviderResponse)
def configure_ai_provider(request: AIProviderRequest, store: ConfigStoreDep) -> AIProviderResponse:
    config = store.load()
    if config.vault_path is None:
        raise api_error(
            "SESSION_STATE_ERROR", "Configure the vault before selecting a provider", 409
        )

    config.provider_id = request.provider_id.value
    config.model = request.model
    config.base_url = request.base_url
    config.fallback_model = request.fallback_model
    if config.onboarding_step != OnboardingStep.COMPLETE:
        config.onboarding_step = _advance_to(config.onboarding_step, OnboardingStep.AI_PROVIDER)

    store.save(config)
    return AIProviderResponse(onboarding_step=config.onboarding_step)


@router.get("/ollama/models", response_model=OllamaModelsResponse)
async def list_installed_ollama_models(
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
) -> OllamaModelsResponse:
    try:
        return OllamaModelsResponse(models=await list_ollama_models(base_url))
    except (AIProviderUnavailableError, AIInvalidOutputError) as exc:
        raise api_error("AI_UNAVAILABLE", str(exc), 503) from exc


@router.post("/ai-provider/validate", response_model=ValidateResponse)
async def validate_ai_provider(
    request: ValidateRequest,
    store: ConfigStoreDep,
    credential_store: CredentialStoreDep,
) -> ValidateResponse:
    config = store.load()
    if config.provider_id is None or config.model is None:
        raise api_error("SESSION_STATE_ERROR", "Select a provider and model before validating", 409)

    provider_id = ProviderId(config.provider_id)
    # A key saved earlier for this same provider is reused when none is
    # typed, so switching away and back never forces re-entering it
    # (docs/TASKS.md T162, user request).
    saved = next((p for p in config.ai_providers if p.provider_id == provider_id), None)
    credential = request.credential
    if credential is None and saved is not None and saved.credential_ref is not None:
        credential = credential_store.get(saved.credential_ref)

    result = check_provider_capability(
        provider_id=provider_id,
        model=config.model,
        base_url=config.base_url,
        credential=credential,
    )
    if result.ok:
        result = await validate_provider_connection(
            provider_id=provider_id,
            model=config.model,
            base_url=config.base_url,
            credential=credential,
        )
    if not result.ok:
        return ValidateResponse(
            onboarding_step=config.onboarding_step, ok=False, reason=result.reason
        )

    credential_ref = saved.credential_ref if saved is not None else None
    if request.credential is not None:
        # Same ref overwritten in the keyring, not a fresh one per save --
        # otherwise every re-entered key would orphan the previous entry.
        credential_ref = credential_ref or new_credential_ref(provider_id.value)
        credential_store.set(credential_ref, request.credential)

    fields = {
        "model": config.model,
        "base_url": config.base_url,
        "credential_ref": credential_ref,
        "fallback_model": config.fallback_model,
        "enabled": True,
        "is_default": True,
    }
    entry = (
        saved.model_copy(update=fields)
        if saved is not None
        else AIProviderConfig(provider_id=provider_id, **fields)  # type: ignore[arg-type]
    )
    others = [
        p.model_copy(update={"is_default": False})
        for p in config.ai_providers
        if p.provider_id != provider_id
    ]
    config.ai_providers = [*others, entry]
    if config.onboarding_step != OnboardingStep.COMPLETE:
        config.onboarding_step = _advance_to(config.onboarding_step, OnboardingStep.VALIDATE)

    store.save(config)
    return ValidateResponse(onboarding_step=config.onboarding_step, ok=True)


@router.post("/complete", response_model=CompleteResponse)
def complete_onboarding(store: ConfigStoreDep) -> CompleteResponse:
    config = store.load()
    if config.onboarding_step == OnboardingStep.COMPLETE:
        return CompleteResponse(onboarding_step=config.onboarding_step)

    if config.vault_path is None:
        raise api_error("SESSION_STATE_ERROR", "Vault is not configured", 409)
    if not any(p.is_default for p in config.ai_providers):
        raise api_error("SESSION_STATE_ERROR", "No validated default AI provider", 409)

    config.onboarding_step = _advance_to(config.onboarding_step, OnboardingStep.COMPLETE)
    store.save(config)
    return CompleteResponse(onboarding_step=config.onboarding_step)
