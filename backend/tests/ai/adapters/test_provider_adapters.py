from app.ai.adapters._openai_compatible_base import OpenAICompatibleAdapter
from app.ai.adapters.anthropic import AnthropicProvider
from app.ai.adapters.nvidia_nim import NvidiaNimProvider
from app.ai.adapters.ollama import OllamaProvider
from app.ai.adapters.openai import OpenAIProvider
from app.ai.adapters.openai_compatible import OpenAICompatibleProvider
from app.ai.adapters.openrouter import OpenRouterProvider
from app.ai.protocol import AIProvider


def _accepts_provider(provider: AIProvider) -> AIProvider:
    """mypy-checked: every adapter must satisfy the AIProvider protocol."""
    return provider


def test_openai_provider_defaults_to_official_api_and_is_openai_compatible() -> None:
    provider = OpenAIProvider(model="gpt-5", api_key="sk-test")
    assert isinstance(provider, OpenAICompatibleAdapter)
    assert provider._base_url == "https://api.openai.com/v1"
    _accepts_provider(provider)


def test_openrouter_provider_defaults_to_openrouter_api() -> None:
    provider = OpenRouterProvider(model="anthropic/claude", api_key="sk-test")
    assert isinstance(provider, OpenAICompatibleAdapter)
    assert provider._base_url == "https://openrouter.ai/api/v1"
    _accepts_provider(provider)


def test_nvidia_nim_provider_requires_explicit_base_url() -> None:
    provider = NvidiaNimProvider(
        model="meta/llama3", api_key="nvapi-test", base_url="https://my-nim.example.com/v1"
    )
    assert isinstance(provider, OpenAICompatibleAdapter)
    assert provider._base_url == "https://my-nim.example.com/v1"
    _accepts_provider(provider)


def test_openai_compatible_provider_api_key_is_optional() -> None:
    provider = OpenAICompatibleProvider(model="local-model", base_url="http://localhost:8080/v1")
    assert isinstance(provider, OpenAICompatibleAdapter)
    assert provider._api_key is None
    _accepts_provider(provider)


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


def test_all_openai_compatible_family_members_share_the_base() -> None:
    members = [
        OpenAIProvider(model="m", api_key="k"),
        OpenRouterProvider(model="m", api_key="k"),
        NvidiaNimProvider(model="m", api_key="k", base_url="https://x.example.com/v1"),
        OpenAICompatibleProvider(model="m", base_url="https://x.example.com/v1"),
    ]
    assert all(isinstance(m, OpenAICompatibleAdapter) for m in members)
