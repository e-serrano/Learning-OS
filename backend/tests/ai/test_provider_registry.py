import pytest

from app.ai.provider_registry import (
    PROVIDER_REGISTRY,
    ProviderId,
    UnknownProviderError,
    get_provider_descriptor,
    list_providers,
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
    mock = get_provider_descriptor(ProviderId.MOCK)
    assert mock.requires_api_key is False
    assert mock.requires_base_url is False


def test_list_providers_returns_all_registered_descriptors() -> None:
    assert len(list_providers()) == len(PROVIDER_REGISTRY)


def test_get_provider_descriptor_returns_matching_id() -> None:
    for provider_id in ProviderId:
        descriptor = get_provider_descriptor(provider_id)
        assert descriptor.id == provider_id


def test_get_provider_descriptor_rejects_unknown_id() -> None:
    with pytest.raises(UnknownProviderError):
        get_provider_descriptor("not_a_real_provider")  # type: ignore[arg-type]


@pytest.mark.parametrize("provider_id", [ProviderId.OPENAI, ProviderId.ANTHROPIC])
def test_remote_providers_require_api_key(provider_id: ProviderId) -> None:
    assert get_provider_descriptor(provider_id).requires_api_key is True
