from app.ai.adapters._openai_compatible_base import OpenAICompatibleAdapter


class OpenAICompatibleProvider(OpenAICompatibleAdapter):
    """Generic OpenAI-compatible endpoint; base_url required, API key
    optional (many local/self-hosted servers don't require one) -- see
    docs/AI_CONTRACTS.md #17."""

    def __init__(self, model: str, base_url: str, api_key: str | None = None) -> None:
        super().__init__(model=model, base_url=base_url, api_key=api_key)
