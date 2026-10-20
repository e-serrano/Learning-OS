"""Builds a live `AIProvider` from the user's saved configuration. Never
returns a `MockProvider` unless the user explicitly configured `mock`
(docs/AGENTS.md #17: mock is a deliberate choice, never a fallback for a
missing credential).
"""

from app.ai.capability_check import build_adapter
from app.ai.protocol import AIProvider
from app.ai.provider_registry import PROVIDER_REGISTRY, ProviderId
from app.ai.retry_policy import RetryingProvider
from app.config.credentials import CredentialStore
from app.config.models import AIProviderConfig


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
    descriptor = PROVIDER_REGISTRY[provider_id]

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

    return build_adapter(provider_id, model, config.base_url, credential)


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

    fallback_adapter: AIProvider | None = None
    if default.fallback_model:
        # Same provider/credential/base_url, just a different model
        # (docs/TASKS.md T148, user request) -- e.g. OpenRouter's free
        # models rate-limit independently, so a second free model is a
        # real fallback rather than retrying the same exhausted one.
        fallback_config = default.model_copy(update={"model": default.fallback_model})
        fallback_adapter = _build_adapter(fallback_config, credential)

    return (
        RetryingProvider(adapter, fallback=fallback_adapter),
        default.provider_id.value,
        default.model,
    )
