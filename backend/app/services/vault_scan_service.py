"""Vault scan -- reindexes the vault and reports a scan summary
(docs/TASKS.md T097, docs/API_SPEC.md #2: `POST /vault/scan`).

`VaultIndexer.reindex()` (T042) already walks and hashes every file and
persists `vault_files`, but its return shape (`list[VaultIndexEntry]`)
carries no "how many changed" or "scan errors" signal, and changing it
would break every existing caller that asserts on it directly (T044's/
T045's tests). This wraps it instead: reads each file's prior
`content_hash` before reindexing, then diffs old vs. new to count
`changed_files`, and calls `scan_markdown_files()` separately (cheap --
a directory walk, no file reads) to surface `errors` that `reindex()`
does not return.
"""

from pydantic import BaseModel
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.obsidian.markdown_scanner import scan_markdown_files
from app.obsidian.vault_index import VaultIndexer
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.models import VaultFileModel


class VaultReindexSummary(BaseModel):
    files_scanned: int
    managed_files: int
    changed_files: int
    errors: list[str]


class VaultScanService:
    def __init__(self, engine: Engine, resolver: VaultResolver) -> None:
        self._engine = engine
        self._resolver = resolver

    def scan(self) -> VaultReindexSummary:
        with DbSession(self._engine) as db:
            previous_hashes = {
                row.path: row.content_hash for row in db.scalars(select(VaultFileModel))
            }

        errors = scan_markdown_files(self._resolver).errors
        entries = VaultIndexer(self._engine, self._resolver).reindex()

        changed = sum(1 for e in entries if previous_hashes.get(e.path) != e.content_hash)
        managed = sum(1 for e in entries if e.managed_id is not None)

        return VaultReindexSummary(
            files_scanned=len(entries),
            managed_files=managed,
            changed_files=changed,
            errors=errors,
        )
