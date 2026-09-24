import keyring
import pytest

from app.config.keyring_setup import configure_container_keyring


def test_noop_when_password_env_var_is_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KEYRING_CRYPTFILE_PASSWORD", raising=False)
    original = keyring.get_keyring()

    configure_container_keyring()

    assert keyring.get_keyring() is original


def test_activates_the_cryptfile_backend_with_the_configured_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KEYRING_CRYPTFILE_PASSWORD", "test-password")
    original = keyring.get_keyring()

    try:
        configure_container_keyring()

        from keyrings.cryptfile.cryptfile import CryptFileKeyring

        active = keyring.get_keyring()
        assert isinstance(active, CryptFileKeyring)
        assert active.keyring_key == "test-password"
    finally:
        keyring.set_keyring(original)
