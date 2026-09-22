from enum import StrEnum

from pydantic import BaseModel


class ProviderId(StrEnum):
    """Required provider IDs -- see docs/AGENTS.md #20 and docs/AI_CONTRACTS.md #16."""

    MOCK = "mock"
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    NVIDIA_NIM = "nvidia_nim"
    OPENAI_COMPATIBLE = "openai_compatible"


class ProviderDescriptor(BaseModel):
    """Declared capabilities for a provider.

    These are hints for onboarding UI/validation flow, not guarantees: the
    actual connection/credential/model/structured-output capability is
    always confirmed live (docs/AI_CONTRACTS.md #19), never assumed.
    """

    id: ProviderId
    display_name: str
    requires_api_key: bool
    requires_base_url: bool
    supports_model_listing: bool
    supports_structured_output: bool
    supports_embeddings: bool
    """Whether this provider's wire protocol has an embeddings endpoint at
    all (docs/TASKS.md T128) -- Anthropic has none. This is a protocol
    capability, not a guarantee this deployment has a working default
    embedding model configured for it -- see
    `app/ai/embedding_provider_factory.py`'s `DEFAULT_EMBEDDING_MODELS`."""


PROVIDER_REGISTRY: dict[ProviderId, ProviderDescriptor] = {
    ProviderId.MOCK: ProviderDescriptor(
        id=ProviderId.MOCK,
        display_name="Mock (offline, deterministic)",
        requires_api_key=False,
        requires_base_url=False,
        supports_model_listing=False,
        supports_structured_output=True,
        supports_embeddings=True,
    ),
    ProviderId.OLLAMA: ProviderDescriptor(
        id=ProviderId.OLLAMA,
        display_name="Ollama (local)",
        requires_api_key=False,
        requires_base_url=True,
        supports_model_listing=True,
        supports_structured_output=True,
        supports_embeddings=True,
    ),
    ProviderId.OPENAI: ProviderDescriptor(
        id=ProviderId.OPENAI,
        display_name="OpenAI",
        requires_api_key=True,
        requires_base_url=False,
        supports_model_listing=True,
        supports_structured_output=True,
        supports_embeddings=True,
    ),
    ProviderId.ANTHROPIC: ProviderDescriptor(
        id=ProviderId.ANTHROPIC,
        display_name="Anthropic / Claude",
        requires_api_key=True,
        requires_base_url=False,
        supports_model_listing=True,
        supports_structured_output=True,
        supports_embeddings=False,
    ),
    ProviderId.OPENROUTER: ProviderDescriptor(
        id=ProviderId.OPENROUTER,
        display_name="OpenRouter",
        requires_api_key=True,
        requires_base_url=True,
        supports_model_listing=True,
        supports_structured_output=True,
        supports_embeddings=True,
    ),
    ProviderId.NVIDIA_NIM: ProviderDescriptor(
        id=ProviderId.NVIDIA_NIM,
        display_name="NVIDIA NIM/API",
        requires_api_key=True,
        requires_base_url=True,
        supports_model_listing=True,
        supports_structured_output=True,
        supports_embeddings=True,
    ),
    ProviderId.OPENAI_COMPATIBLE: ProviderDescriptor(
        id=ProviderId.OPENAI_COMPATIBLE,
        display_name="OpenAI-compatible",
        requires_api_key=False,
        requires_base_url=True,
        supports_model_listing=True,
        supports_structured_output=False,
        supports_embeddings=True,
    ),
}


class UnknownProviderError(ValueError):
    def __init__(self, provider_id: str) -> None:
        super().__init__(f"Unknown provider id: {provider_id!r}")


def list_providers() -> list[ProviderDescriptor]:
    return list(PROVIDER_REGISTRY.values())


def get_provider_descriptor(provider_id: ProviderId) -> ProviderDescriptor:
    try:
        return PROVIDER_REGISTRY[provider_id]
    except KeyError as exc:
        raise UnknownProviderError(provider_id) from exc
