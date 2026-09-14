from typing import Protocol
from uuid import uuid4

import keyring
import keyring.errors

SERVICE_NAME = "learning-os"


class KeyringBackend(Protocol):
    """Structural interface satisfied by the `keyring` module itself.

    Kept separate so tests can inject an in-memory fake instead of touching
    the real OS credential store -- see docs/AGENTS.md #17 (mock provider
    for deterministic tests).
    """

    def set_password(self, service_name: str, username: str, password: str) -> None: ...

    def get_password(self, service_name: str, username: str) -> str | None: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


def new_credential_ref(provider_id: str) -> str:
    """Generate an opaque reference for a stored credential.

    This value -- never the secret -- is what gets persisted in AppConfig /
    ai_provider_configs. See docs/AGENTS.md #21.
    """
    return f"{provider_id}:{uuid4().hex}"


class CredentialStore:
    """Stores/retrieves API credentials via the OS keyring.

    Secrets never pass through SQLite, Markdown, Git, logs, or frontend
    storage -- callers only ever hold a `credential_ref`.
    """

    def __init__(self, backend: KeyringBackend | None = None) -> None:
        self._backend: KeyringBackend = backend if backend is not None else keyring

    def set(self, credential_ref: str, secret: str) -> None:
        self._backend.set_password(SERVICE_NAME, credential_ref, secret)

    def get(self, credential_ref: str) -> str | None:
        return self._backend.get_password(SERVICE_NAME, credential_ref)

    def delete(self, credential_ref: str) -> None:
        try:
            self._backend.delete_password(SERVICE_NAME, credential_ref)
        except keyring.errors.PasswordDeleteError:
            pass
