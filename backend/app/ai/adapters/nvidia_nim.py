from app.ai.adapters._openai_compatible_base import OpenAICompatibleAdapter


class NvidiaNimProvider(OpenAICompatibleAdapter):
    """NVIDIA NIM/API; endpoint and model are configurable -- no default
    base_url, since NIM can be self-hosted or the hosted API -- see
    docs/AI_CONTRACTS.md #17 and docs/AGENTS.md #20."""

    def __init__(self, model: str, api_key: str, base_url: str) -> None:
        super().__init__(model=model, base_url=base_url, api_key=api_key)
