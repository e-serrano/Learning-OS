import os
from pathlib import Path

from pydantic import BaseModel


class VaultScanResult(BaseModel):
    """Read-only scan result for onboarding's VAULT_SCAN step.

    Deliberately minimal (existence/readability + markdown file count) --
    the full recursive scanner with frontmatter, managed sections, hashing,
    and indexing is built in T037-T038 (Phase 3). This never writes
    anything, matching docs/OBSIDIAN_SCHEMA.md #13 "first run is read-only".
    """

    exists: bool
    readable: bool
    markdown_file_count: int
    errors: list[str]


def scan_vault_readonly(path: str) -> VaultScanResult:
    root = Path(path)

    if not root.exists():
        return VaultScanResult(
            exists=False, readable=False, markdown_file_count=0, errors=["Path does not exist"]
        )
    if not root.is_dir():
        return VaultScanResult(
            exists=True, readable=False, markdown_file_count=0, errors=["Path is not a directory"]
        )
    if not os.access(root, os.R_OK):
        return VaultScanResult(
            exists=True, readable=False, markdown_file_count=0, errors=["Path is not readable"]
        )

    count = 0
    errors: list[str] = []
    try:
        for entry in root.rglob("*.md"):
            if ".obsidian" in entry.parts:
                continue
            count += 1
    except OSError as exc:
        errors.append(str(exc))

    return VaultScanResult(
        exists=True, readable=True, markdown_file_count=count, errors=errors
    )
