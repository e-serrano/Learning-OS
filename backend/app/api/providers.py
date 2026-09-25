"""Provider configuration routes (docs/TASKS.md T099, docs/API_SPEC.md #14).

Standalone counterparts to the `/onboarding/ai-provider*` routes (T025)
-- same relationship T097's `/vault/*` has to `/onboarding/vault`. Only
read + validate here, no save/update route: the task text ("Leer
configuracion sin secretos y validar provider/model") names exactly
those two capabilities. Provider configs are still only ever *written*
through `/onboarding/ai-provider`+`/ai-provider/validate` -- but despite
the URL prefix those two remain fully callable after onboarding
`COMPLETE` (neither route gates on onboarding step for anything beyond
advancing the state machine, which they simply skip once already
complete). `AIProviderSettings.tsx` (docs/TASKS.md T146) is exactly
that: the frontend reusing them from Settings to change provider/model
/credential later, not a new backend route.

Never returns `credential_ref` (docs/API_SPEC.md #14: "Configuration
endpoints must never return API keys") even though it is only a keyring
lookup key, not the secret itself -- omitting it entirely is simpler to
defend than reasoning about what a lookup key could leak.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.ai.capability_check import (
    CapabilityCheckResult,
    check_provider_capability,
    validate_provider_connection,
)
from app.ai.provider_registry import ProviderDescriptor, ProviderId, list_providers
from app.api.dependencies import get_config_store
from app.config.store import ConfigStore

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])

ConfigStoreDep = Annotated[ConfigStore, Depends(get_config_store)]


class ConfiguredProvider(BaseModel):
    provider_id: ProviderId
    model: str
    base_url: str | None
    fallback_model: str | None
    enabled: bool
    is_default: bool


class ProviderConfigResponse(BaseModel):
    provider_id: str | None
    model: str | None
    base_url: str | None
    ai_providers: list[ConfiguredProvider]


class ValidateProviderRequest(BaseModel):
    provider_id: ProviderId
    model: str | None = None
    base_url: str | None = None
    credential: str | None = None


@router.get("", response_model=list[ProviderDescriptor])
def list_supported_providers() -> list[ProviderDescriptor]:
    return list_providers()


@router.get("/config", response_model=ProviderConfigResponse)
def get_provider_config(store: ConfigStoreDep) -> ProviderConfigResponse:
    config = store.load()
    return ProviderConfigResponse(
        provider_id=config.provider_id,
        model=config.model,
        base_url=config.base_url,
        ai_providers=[
            ConfiguredProvider(
                provider_id=p.provider_id,
                model=p.model,
                base_url=p.base_url,
                fallback_model=p.fallback_model,
                enabled=p.enabled,
                is_default=p.is_default,
            )
            for p in config.ai_providers
        ],
    )


@router.post("/validate", response_model=CapabilityCheckResult)
async def validate_provider(request: ValidateProviderRequest) -> CapabilityCheckResult:
    result = check_provider_capability(
        provider_id=request.provider_id,
        model=request.model,
        base_url=request.base_url,
        credential=request.credential,
    )
    if result.ok:
        assert request.model is not None  # guaranteed by check_provider_capability's own check
        result = await validate_provider_connection(
            provider_id=request.provider_id,
            model=request.model,
            base_url=request.base_url,
            credential=request.credential,
        )
    return result
