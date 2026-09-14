import keyring.errors
import pytest

from app.config.credentials import SERVICE_NAME, CredentialStore, new_credential_ref


class FakeKeyringBackend:
    """In-memory stand-in for the OS keyring, used only in tests."""

    def __init__(self) -> None:
        self._data: dict[tuple[str, str], str] = {}

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self._data[(service_name, username)] = password

    def get_password(self, service_name: str, username: str) -> str | None:
        return self._data.get((service_name, username))

    def delete_password(self, service_name: str, username: str) -> None:
        key = (service_name, username)
        if key not in self._data:
            raise keyring.errors.PasswordDeleteError("not found")
        del self._data[key]


def test_new_credential_ref_is_opaque_and_unique() -> None:
    ref1 = new_credential_ref("openai")
    ref2 = new_credential_ref("openai")
    assert ref1 != ref2
    assert ref1.startswith("openai:")


def test_set_then_get_roundtrips_secret() -> None:
    store = CredentialStore(backend=FakeKeyringBackend())
    ref = new_credential_ref("anthropic")
    store.set(ref, "sk-super-secret")
    assert store.get(ref) == "sk-super-secret"


def test_get_missing_credential_returns_none() -> None:
    store = CredentialStore(backend=FakeKeyringBackend())
    assert store.get("nvidia_nim:does-not-exist") is None


def test_delete_removes_credential() -> None:
    store = CredentialStore(backend=FakeKeyringBackend())
    ref = new_credential_ref("openrouter")
    store.set(ref, "secret-value")
    store.delete(ref)
    assert store.get(ref) is None


def test_delete_missing_credential_is_idempotent() -> None:
    store = CredentialStore(backend=FakeKeyringBackend())
    store.delete("openai:never-existed")  # must not raise


def test_credentials_are_scoped_to_learning_os_service() -> None:
    backend = FakeKeyringBackend()
    store = CredentialStore(backend=backend)
    ref = new_credential_ref("ollama")
    store.set(ref, "secret-value")
    assert (SERVICE_NAME, ref) in backend._data


def test_credential_store_repr_never_leaks_secrets() -> None:
    store = CredentialStore(backend=FakeKeyringBackend())
    ref = new_credential_ref("openai")
    store.set(ref, "sk-should-not-appear-anywhere")
    assert "sk-should-not-appear-anywhere" not in repr(store)


@pytest.mark.parametrize("provider_id", ["openai", "anthropic", "openrouter", "nvidia_nim"])
def test_new_credential_ref_supports_required_remote_providers(provider_id: str) -> None:
    assert new_credential_ref(provider_id).startswith(f"{provider_id}:")
