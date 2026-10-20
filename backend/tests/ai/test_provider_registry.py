import pytest

from app.ai.provider_registry import (
    PROVIDER_REGISTRY,
    ProviderId,
)

REQUIRED_IDS = {
    "mock",
    "ollama",
    "openai",
    "anthropic",
    "openrouter",
    "nvidia_nim",
    "openai_compatible",
}


def test_registry_has_exactly_the_required_provider_ids() -> None:
    assert {p.value for p in ProviderId} == REQUIRED_IDS
    assert {d.id.value for d in PROVIDER_REGISTRY.values()} == REQUIRED_IDS


def test_mock_provider_never_requires_credentials_or_endpoint() -> None:
    mock = PROVIDER_REGISTRY[ProviderId.MOCK]
    assert mock.requires_api_key is False
    assert mock.requires_base_url is False


@pytest.mark.parametrize("provider_id", [ProviderId.OPENAI, ProviderId.ANTHROPIC])
def test_remote_providers_require_api_key(provider_id: ProviderId) -> None:
    assert PROVIDER_REGISTRY[provider_id].requires_api_key is True


def test_anthropic_has_no_embeddings_endpoint() -> None:
    """docs/TASKS.md T128: Anthropic has no embeddings API at all -- the
    one provider that's structurally excluded, not just missing a
    configured default model."""
    assert PROVIDER_REGISTRY[ProviderId.ANTHROPIC].supports_embeddings is False


@pytest.mark.parametrize(
    "provider_id",
    [
        ProviderId.MOCK,
        ProviderId.OLLAMA,
        ProviderId.OPENAI,
        ProviderId.OPENROUTER,
        ProviderId.NVIDIA_NIM,
        ProviderId.OPENAI_COMPATIBLE,
    ],
)
def test_every_other_provider_supports_embeddings(provider_id: ProviderId) -> None:
    assert PROVIDER_REGISTRY[provider_id].supports_embeddings is True
