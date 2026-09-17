"""Builds a live `AIProvider` from the user's saved configuration
(docs/TASKS.md T101 -- the first route to actually call the AI
orchestrator over HTTP). Every provider-calling route from here on
(T101-T106) shares this one factory instead of re-deriving "which
adapter, which credential" each time.

Never returns a `MockProvider` unless the user explicitly configured
`mock` as their default provider (docs/AGENTS.md #17: mock is a
deliberate, legitimate choice -- never an automatic fallback for a
missing credential).

Reuses `PROVIDER_REGISTRY`'s `requires_api_key`/`requires_base_url`
flags (the same ones `check_provider_capability`, T018, already checks)
rather than re-deriving "which provider needs what" a third time.
"""

from app.ai.adapters.anthropic import AnthropicProvider
from app.ai.adapters.mock import MockProvider
from app.ai.adapters.nvidia_nim import NvidiaNimProvider
from app.ai.adapters.ollama import OllamaProvider
from app.ai.adapters.openai import OpenAIProvider
from app.ai.adapters.openai_compatible import OpenAICompatibleProvider
from app.ai.adapters.openrouter import OpenRouterProvider
from app.ai.protocol import AIProvider
from app.ai.provider_registry import ProviderId, get_provider_descriptor
from app.ai.retry_policy import RetryingProvider
from app.config.credentials import CredentialStore
from app.config.models import AIProviderConfig

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


class NoDefaultProviderError(Exception):
    pass


class MissingCredentialError(Exception):
    pass


class MissingBaseUrlError(Exception):
    pass


def _resolve_credential(config: AIProviderConfig, credentials: CredentialStore) -> str | None:
    if config.credential_ref is None:
        return None
    return credentials.get(config.credential_ref)


def _build_adapter(config: AIProviderConfig, credential: str | None) -> AIProvider:
    provider_id = config.provider_id
    model = config.model
    descriptor = get_provider_descriptor(provider_id)

    if descriptor.requires_api_key and credential is None:
        raise MissingCredentialError(f"provider {provider_id!r} requires a credential")
    # Ollama has a sensible local default, so it is exempt from the
    # generic requires_base_url gate below even though the registry
    # marks it required for onboarding UI purposes.
    if (
        descriptor.requires_base_url
        and config.base_url is None
        and provider_id != ProviderId.OLLAMA
    ):
        raise MissingBaseUrlError(f"provider {provider_id!r} requires a base_url")

    if provider_id == ProviderId.MOCK:
        return MockProvider()
    if provider_id == ProviderId.OLLAMA:
        return OllamaProvider(model=model, base_url=config.base_url or DEFAULT_OLLAMA_BASE_URL)
    if provider_id == ProviderId.OPENAI:
        assert credential is not None
        return OpenAIProvider(model=model, api_key=credential)
    if provider_id == ProviderId.ANTHROPIC:
        assert credential is not None
        return AnthropicProvider(model=model, api_key=credential)
    if provider_id == ProviderId.OPENROUTER:
        assert credential is not None
        assert config.base_url is not None
        return OpenRouterProvider(model=model, api_key=credential, base_url=config.base_url)
    if provider_id == ProviderId.NVIDIA_NIM:
        assert credential is not None
        assert config.base_url is not None
        return NvidiaNimProvider(model=model, api_key=credential, base_url=config.base_url)
    if provider_id == ProviderId.OPENAI_COMPATIBLE:
        assert config.base_url is not None
        return OpenAICompatibleProvider(model=model, base_url=config.base_url, api_key=credential)

    raise ValueError(f"unknown provider id: {provider_id!r}")


def build_default_provider(
    ai_providers: list[AIProviderConfig], credentials: CredentialStore
) -> tuple[AIProvider, str, str]:
    """Returns `(provider, provider_name, model)` for the configured
    default provider, ready to hand to `AIOrchestrator`."""
    default = next((p for p in ai_providers if p.is_default and p.enabled), None)
    if default is None:
        raise NoDefaultProviderError("no enabled default AI provider is configured")

    credential = _resolve_credential(default, credentials)
    adapter = _build_adapter(default, credential)
    return RetryingProvider(adapter), default.provider_id.value, default.model
