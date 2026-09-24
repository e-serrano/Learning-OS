"""Encrypted-file keyring backend for environments with no OS credential
store (docs/TASKS.md T143: Docker/Linux containers).

`CredentialStore` (docs/AGENTS.md #21) delegates to the `keyring` library,
which picks Windows Credential Manager / macOS Keychain automatically on
those platforms -- nothing to configure there. Inside a minimal Linux
container there is no such backend available, so a bare `keyring.set_password`
call raises `NoKeyringError` the first time onboarding tries to store a
credential.

This only activates when `KEYRING_CRYPTFILE_PASSWORD` is set, which the
Docker image's entrypoint is the only thing that ever sets -- so a native
dev/prod run (no such variable) is completely unaffected and keeps using
the real OS keyring exactly as before. The encrypted credential file's
location follows `XDG_DATA_HOME`/`HOME` (the Docker image sets
`HOME=/data`, the same persistent volume the SQLite DB lives in), so
credentials survive container recreation the same way the DB does.
"""

import os


def configure_container_keyring() -> None:
    password = os.environ.get("KEYRING_CRYPTFILE_PASSWORD")
    if not password:
        return

    import keyring
    from keyrings.cryptfile.cryptfile import CryptFileKeyring  # type: ignore[import-untyped]

    backend = CryptFileKeyring()
    backend.keyring_key = password
    keyring.set_keyring(backend)
