import pytest

from app.ai.adapters.mock_embeddings import MockEmbeddingProvider
from app.ai.adapters.ollama_embeddings import OllamaEmbeddingProvider
from app.ai.adapters.openai_embeddings import OpenAIEmbeddingProvider
from app.ai.embedding_provider_factory import (
    MissingCredentialError,
    NoDefaultEmbeddingModelError,
    NoDefaultProviderError,
    ProviderHasNoEmbeddingSupportError,
    build_default_embedding_provider,
)
from app.ai.provider_registry import ProviderId
from app.config.credentials import CredentialStore
from app.config.models import AIProviderConfig


class FakeKeyringBackend:
    def __init__(self) -> None:
        self._data: dict[tuple[str, str], str] = {}

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self._data[(service_name, username)] = password

    def get_password(self, service_name: str, username: str) -> str | None:
        return self._data.get((service_name, username))

    def delete_password(self, service_name: str, username: str) -> None:
        del self._data[(service_name, username)]


def _credentials(**stored: str) -> CredentialStore:
    backend = FakeKeyringBackend()
    store = CredentialStore(backend=backend)
    for ref, value in stored.items():
        store.set(ref, value)
    return store


def test_raises_when_none_marked_default() -> None:
    with pytest.raises(NoDefaultProviderError):
        build_default_embedding_provider([], _credentials())


def test_raises_when_default_provider_has_no_embeddings_endpoint() -> None:
    """Anthropic -- has no embeddings API at all."""
    configs = [
        AIProviderConfig(provider_id=ProviderId.ANTHROPIC, model="claude-x", is_default=True)
    ]

    with pytest.raises(ProviderHasNoEmbeddingSupportError):
        build_default_embedding_provider(configs, _credentials())


def test_raises_when_no_default_embedding_model_for_provider() -> None:
    """OpenRouter supports embeddings in principle but has no universal
    safe default model id to hardcode."""
    configs = [
        AIProviderConfig(
            provider_id=ProviderId.OPENROUTER,
            model="anthropic/claude",
            base_url="https://openrouter.ai/api/v1",
            is_default=True,
        )
    ]

    with pytest.raises(NoDefaultEmbeddingModelError):
        build_default_embedding_provider(configs, _credentials())


def test_returns_mock_embedding_provider() -> None:
    configs = [AIProviderConfig(provider_id=ProviderId.MOCK, model="mock-1", is_default=True)]

    provider, name, model = build_default_embedding_provider(configs, _credentials())

    assert isinstance(provider, MockEmbeddingProvider)
    assert name == "mock"
    assert model == "mock-embed"


def test_returns_ollama_embedding_provider_with_default_local_url() -> None:
    configs = [AIProviderConfig(provider_id=ProviderId.OLLAMA, model="llama3", is_default=True)]

    provider, name, model = build_default_embedding_provider(configs, _credentials())

    assert isinstance(provider, OllamaEmbeddingProvider)
    assert name == "ollama"
    assert model == "nomic-embed-text"


def test_returns_openai_embedding_provider_with_resolved_credential() -> None:
    configs = [
        AIProviderConfig(
            provider_id=ProviderId.OPENAI,
            model="gpt-5",
            credential_ref="cred_1",
            is_default=True,
        )
    ]
    credentials = _credentials(cred_1="sk-secret")

    provider, name, model = build_default_embedding_provider(configs, credentials)

    assert isinstance(provider, OpenAIEmbeddingProvider)
    assert name == "openai"
    assert model == "text-embedding-3-small"


def test_raises_when_openai_credential_missing() -> None:
    configs = [AIProviderConfig(provider_id=ProviderId.OPENAI, model="gpt-5", is_default=True)]

    with pytest.raises(MissingCredentialError):
        build_default_embedding_provider(configs, _credentials())
