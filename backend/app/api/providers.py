"""Provider configuration routes (docs/TASKS.md T099, docs/API_SPEC.md #14).

Standalone counterparts to the onboarding-only `/onboarding/ai-provider*`
routes (T025) -- same relationship T097's `/vault/*` has to
`/onboarding/vault`. Only read + validate, no save/update route: the
task text ("Leer configuracion sin secretos y validar provider/model")
names exactly those two capabilities, and provider configs are still
only ever written through onboarding (T025) -- changing an already
-configured default provider post-onboarding is out of scope here.

Never returns `credential_ref` (docs/API_SPEC.md #14: "Configuration
endpoints must never return API keys") even though it is only a keyring
lookup key, not the secret itself -- omitting it entirely is simpler to
defend than reasoning about what a lookup key could leak.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.ai.capability_check import CapabilityCheckResult, check_provider_capability
from app.ai.provider_registry import ProviderDescriptor, ProviderId, list_providers
from app.api.dependencies import get_config_store
from app.config.store import ConfigStore

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])

ConfigStoreDep = Annotated[ConfigStore, Depends(get_config_store)]


class ConfiguredProvider(BaseModel):
    provider_id: ProviderId
    model: str
    base_url: str | None
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
                enabled=p.enabled,
                is_default=p.is_default,
            )
            for p in config.ai_providers
        ],
    )


@router.post("/validate", response_model=CapabilityCheckResult)
def validate_provider(request: ValidateProviderRequest) -> CapabilityCheckResult:
    return check_provider_capability(
        provider_id=request.provider_id,
        model=request.model,
        base_url=request.base_url,
        credential=request.credential,
    )
