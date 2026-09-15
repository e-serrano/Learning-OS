from app.ai.adapters._openai_compatible_base import OpenAICompatibleAdapter


class OpenRouterProvider(OpenAICompatibleAdapter):
    """OpenRouter API; model IDs are configurable -- see docs/AI_CONTRACTS.md #17."""

    def __init__(
        self, model: str, api_key: str, base_url: str = "https://openrouter.ai/api/v1"
    ) -> None:
        super().__init__(model=model, base_url=base_url, api_key=api_key)
