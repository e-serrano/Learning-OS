"""Builds a live `EmbeddingProvider` from the user's default AI provider
config (mirrors `provider_factory.py`), reusing its credential/base_url.

Chat and embedding models differ, so a fixed embedding model is picked per
provider in `DEFAULT_EMBEDDING_MODELS`. Providers absent from it (Anthropic
has no embeddings endpoint; OpenRouter/NIM/OpenAI-compatible have no safe
universal default model id) raise `ProviderHasNoEmbeddingSupportError`.
"""

from app.ai.adapters.mock_embeddings import MockEmbeddingProvider
from app.ai.adapters.ollama_embeddings import OllamaEmbeddingProvider
from app.ai.adapters.openai_embeddings import OpenAIEmbeddingProvider
from app.ai.capability_check import DEFAULT_OLLAMA_BASE_URL
from app.ai.embedding_protocol import EmbeddingProvider
from app.ai.provider_factory import (
    MissingCredentialError,
    NoDefaultProviderError,
)
from app.ai.provider_registry import ProviderId
from app.config.credentials import CredentialStore
from app.config.models import AIProviderConfig

__all__ = [
    "MissingCredentialError",
    "NoDefaultProviderError",
    "ProviderHasNoEmbeddingSupportError",
    "build_default_embedding_provider",
]

DEFAULT_EMBEDDING_MODELS: dict[ProviderId, str] = {
    ProviderId.MOCK: "mock-embed",
    ProviderId.OLLAMA: "nomic-embed-text",
    ProviderId.OPENAI: "text-embedding-3-small",
}


class ProviderHasNoEmbeddingSupportError(Exception):
    pass


def build_default_embedding_provider(
    ai_providers: list[AIProviderConfig], credentials: CredentialStore
) -> tuple[EmbeddingProvider, str, str]:
    """Returns `(provider, provider_name, model)` for the user's
    configured default AI provider's embeddings capability, ready to
    hand to `EmbeddingOrchestrator`."""
    default = next((p for p in ai_providers if p.is_default and p.enabled), None)
    if default is None:
        raise NoDefaultProviderError("no enabled default AI provider is configured")

    provider_id = default.provider_id
    model = DEFAULT_EMBEDDING_MODELS.get(provider_id)
    if model is None:
        raise ProviderHasNoEmbeddingSupportError(
            f"provider {provider_id!r} has no default embedding model"
        )

    if provider_id == ProviderId.MOCK:
        return MockEmbeddingProvider(), provider_id.value, model
    if provider_id == ProviderId.OLLAMA:
        return (
            OllamaEmbeddingProvider(
                model=model, base_url=default.base_url or DEFAULT_OLLAMA_BASE_URL
            ),
            provider_id.value,
            model,
        )
    # Only OpenAI remains in `DEFAULT_EMBEDDING_MODELS`.
    credential = default.credential_ref and credentials.get(default.credential_ref)
    if credential is None:
        raise MissingCredentialError(f"provider {provider_id!r} requires a credential")
    return OpenAIEmbeddingProvider(model=model, api_key=credential), provider_id.value, model
