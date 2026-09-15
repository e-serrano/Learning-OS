from pydantic import BaseModel

from app.obsidian.vault_resolver import VaultResolver

DEFAULT_IGNORED_DIRS = frozenset({".obsidian", "Attachments", "Templates"})
"""See docs/OBSIDIAN_SCHEMA.md #14. .obsidian is never scanned regardless."""


class ScannedFile(BaseModel):
    path: str
    """Vault-relative, POSIX-style (forward slashes) for stable IDs across OSes."""


class ScanResult(BaseModel):
    files: list[ScannedFile]
    errors: list[str]


def scan_markdown_files(
    resolver: VaultResolver, ignored_dirs: frozenset[str] = DEFAULT_IGNORED_DIRS
) -> ScanResult:
    """Recursively, read-only enumerate Markdown files under the vault root.

    Never writes anything -- see docs/OBSIDIAN_SCHEMA.md #13. Feeds the
    vault index (T042); onboarding's own summary scan is unrelated.
    """
    files: list[ScannedFile] = []
    errors: list[str] = []

    try:
        for entry in sorted(resolver.root.rglob("*.md")):
            relative_parts = entry.relative_to(resolver.root).parts
            if any(part in ignored_dirs for part in relative_parts[:-1]):
                continue
            files.append(ScannedFile(path=entry.relative_to(resolver.root).as_posix()))
    except OSError as exc:
        errors.append(str(exc))

    return ScanResult(files=files, errors=errors)
