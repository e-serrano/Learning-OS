from app.ai.adapters._openai_compatible_base import OpenAICompatibleAdapter
from app.ai.adapters.anthropic import AnthropicProvider
from app.ai.adapters.ollama import OllamaProvider
from app.ai.protocol import AIProvider


def _accepts_provider(provider: AIProvider) -> AIProvider:
    """mypy-checked: every adapter must satisfy the AIProvider protocol."""
    return provider


def test_ollama_provider_defaults_to_localhost() -> None:
    provider = OllamaProvider(model="llama3")
    assert provider._base_url == "http://localhost:11434"
    _accepts_provider(provider)


def test_ollama_provider_is_not_openai_compatible_subclass() -> None:
    """Ollama uses its own native protocol, not the shared HTTP base."""
    assert not isinstance(OllamaProvider(model="llama3"), OpenAICompatibleAdapter)


def test_anthropic_provider_defaults_to_official_api() -> None:
    provider = AnthropicProvider(model="claude-opus-5", api_key="sk-ant-test")
    assert provider._base_url == "https://api.anthropic.com/v1"
    _accepts_provider(provider)


def test_anthropic_provider_is_not_openai_compatible_subclass() -> None:
    """Anthropic is never treated as OpenAI-compatible -- see docs/AGENTS.md #20."""
    provider = AnthropicProvider(model="claude-opus-5", api_key="sk-ant-test")
    assert not isinstance(provider, OpenAICompatibleAdapter)
