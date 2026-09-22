from app.ai.adapters._openai_compatible_embeddings_base import OpenAICompatibleEmbeddingAdapter
from app.ai.adapters.openai_embeddings import OpenAIEmbeddingProvider
from app.ai.embedding_protocol import EmbeddingProvider


def _accepts_provider(provider: EmbeddingProvider) -> EmbeddingProvider:
    """mypy-checked: the adapter must satisfy the EmbeddingProvider protocol."""
    return provider


def test_openai_embedding_provider_defaults_to_official_api_and_is_openai_compatible() -> None:
    provider = OpenAIEmbeddingProvider(model="text-embedding-3-small", api_key="sk-test")
    assert isinstance(provider, OpenAICompatibleEmbeddingAdapter)
    assert provider._base_url == "https://api.openai.com/v1"
    _accepts_provider(provider)
