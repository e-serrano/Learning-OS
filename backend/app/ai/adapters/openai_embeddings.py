from app.ai.adapters._openai_compatible_embeddings_base import OpenAICompatibleEmbeddingAdapter


class OpenAIEmbeddingProvider(OpenAICompatibleEmbeddingAdapter):
    """Direct OpenAI embeddings API -- see docs/TASKS.md T128."""

    def __init__(
        self, model: str, api_key: str, base_url: str = "https://api.openai.com/v1"
    ) -> None:
        super().__init__(model=model, base_url=base_url, api_key=api_key)
