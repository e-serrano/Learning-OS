import pytest

from app.ai.provider_factory import (
    MissingBaseUrlError,
    MissingCredentialError,
    NoDefaultProviderError,
    build_default_provider,
)
from app.ai.provider_registry import ProviderId
from app.ai.retry_policy import RetryingProvider
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


def test_build_default_provider_raises_when_none_marked_default() -> None:
    with pytest.raises(NoDefaultProviderError):
        build_default_provider([], _credentials())


def test_build_default_provider_ignores_disabled_default() -> None:
    configs = [
        AIProviderConfig(
            provider_id=ProviderId.MOCK, model="mock-1", is_default=True, enabled=False
        )
    ]

    with pytest.raises(NoDefaultProviderError):
        build_default_provider(configs, _credentials())


def test_build_default_provider_returns_mock_provider() -> None:
    configs = [AIProviderConfig(provider_id=ProviderId.MOCK, model="mock-1", is_default=True)]

    provider, name, model = build_default_provider(configs, _credentials())

    assert isinstance(provider, RetryingProvider)
    assert name == "mock"
    assert model == "mock-1"


def test_build_default_provider_resolves_credential_from_ref() -> None:
    configs = [
        AIProviderConfig(
            provider_id=ProviderId.ANTHROPIC,
            model="claude-x",
            credential_ref="cred_1",
            is_default=True,
        )
    ]
    credentials = _credentials(cred_1="sk-secret")

    provider, name, model = build_default_provider(configs, credentials)

    assert isinstance(provider, RetryingProvider)
    assert name == "anthropic"


def test_build_default_provider_raises_when_credential_missing() -> None:
    configs = [AIProviderConfig(provider_id=ProviderId.OPENAI, model="gpt-5", is_default=True)]

    with pytest.raises(MissingCredentialError):
        build_default_provider(configs, _credentials())


def test_build_default_provider_raises_when_base_url_missing() -> None:
    configs = [
        AIProviderConfig(
            provider_id=ProviderId.OPENAI_COMPATIBLE, model="local-model", is_default=True
        )
    ]

    with pytest.raises(MissingBaseUrlError):
        build_default_provider(configs, _credentials())


def test_build_default_provider_ollama_defaults_base_url() -> None:
    configs = [AIProviderConfig(provider_id=ProviderId.OLLAMA, model="llama3", is_default=True)]

    provider, _, _ = build_default_provider(configs, _credentials())

    assert isinstance(provider, RetryingProvider)
