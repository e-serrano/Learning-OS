"""Builds a live `EmbeddingProvider` from the user's saved default AI
provider config (docs/TASKS.md T128 -- mirrors `provider_factory.py`).

Reuses the same configured default provider's credential/base_url
(same account, same auth) rather than adding a second, separate
"default embedding provider" concept to `AppConfig` -- there is no
onboarding UI task for choosing one, and this repo already treats
"invent new config surface no task asked for" as out of scope (see
`docs/TASKS.md` T118's/T119's precedent of documenting a gap honestly
instead).

Chat and embedding models are never the same model, though, so a
*separate* fixed model id is picked per provider -- `DEFAULT_EMBEDDING_MODELS`
below -- rather than reusing `config.model` (the user's chosen chat
model, meaningless for an embeddings endpoint). Only three providers
get a real default: Mock and Ollama always work (no cost, no external
model catalog to guess at), and OpenAI's `text-embedding-3-small` is a
stable, well-known default. OpenRouter/NVIDIA NIM/OpenAI-compatible
have no universal safe default embedding model id to hardcode (self-
hosted or per-account model catalogs) -- `NoDefaultEmbeddingModelError`
documents that gap honestly rather than guessing a model id that could
404. Anthropic has no embeddings endpoint at all.
"""

from app.ai.adapters.mock_embeddings import MockEmbeddingProvider
from app.ai.adapters.ollama_embeddings import OllamaEmbeddingProvider
from app.ai.adapters.openai_embeddings import OpenAIEmbeddingProvider
from app.ai.embedding_protocol import EmbeddingProvider
from app.ai.provider_factory import (
    DEFAULT_OLLAMA_BASE_URL,
    MissingCredentialError,
    NoDefaultProviderError,
)
from app.ai.provider_registry import ProviderId, get_provider_descriptor
from app.config.credentials import CredentialStore
from app.config.models import AIProviderConfig

__all__ = [
    "MissingCredentialError",
    "NoDefaultEmbeddingModelError",
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


class NoDefaultEmbeddingModelError(Exception):
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
    descriptor = get_provider_descriptor(provider_id)
    if not descriptor.supports_embeddings:
        raise ProviderHasNoEmbeddingSupportError(
            f"provider {provider_id!r} has no embeddings endpoint"
        )

    model = DEFAULT_EMBEDDING_MODELS.get(provider_id)
    if model is None:
        raise NoDefaultEmbeddingModelError(
            f"no default embedding model configured for provider {provider_id!r}"
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
    if provider_id == ProviderId.OPENAI:
        credential = default.credential_ref and credentials.get(default.credential_ref)
        if credential is None:
            raise MissingCredentialError(f"provider {provider_id!r} requires a credential")
        return OpenAIEmbeddingProvider(model=model, api_key=credential), provider_id.value, model

    raise ProviderHasNoEmbeddingSupportError(f"provider {provider_id!r} has no embeddings endpoint")
