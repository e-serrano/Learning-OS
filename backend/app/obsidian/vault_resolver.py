import os
from pathlib import Path


class VaultUnavailableError(ValueError):
    """Vault root does not exist, isn't a directory, or isn't readable."""


class VaultPathTraversalError(ValueError):
    """A resolved path escapes the configured vault root."""


class VaultResolver:
    """Owns the configured vault root and safely resolves paths inside it.

    Fails fast on construction if the root itself is unusable. `resolve()`
    blocks path traversal (both `../` sequences and absolute-path
    injection) -- see docs/AGENTS.md #19.
    """

    def __init__(self, vault_root: str) -> None:
        root = Path(vault_root)
        if not root.exists():
            raise VaultUnavailableError(f"Vault root does not exist: {vault_root}")
        if not root.is_dir():
            raise VaultUnavailableError(f"Vault root is not a directory: {vault_root}")
        if not os.access(root, os.R_OK):
            raise VaultUnavailableError(f"Vault root is not readable: {vault_root}")
        self.root = root.resolve()

    def resolve(self, relative_path: str) -> Path:
        """Resolve `relative_path` against the vault root.

        Raises VaultPathTraversalError if the result would fall outside the
        root -- covers `../../etc/passwd` style traversal and the pathlib
        gotcha where joining an absolute path discards the base entirely.
        """
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError:
            raise VaultPathTraversalError(
                f"Path escapes vault root: {relative_path}"
            ) from None
        return candidate
