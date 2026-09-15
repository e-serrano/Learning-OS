import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.obsidian.frontmatter import parse_frontmatter
from app.obsidian.hashing import hash_content
from app.obsidian.markdown_scanner import scan_markdown_files
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.models import VaultFileModel

_MANAGED_BY = "learning_os"


class VaultIndexEntry(BaseModel):
    path: str
    content_hash: str
    file_type: str
    managed_id: str | None
    metadata: dict[str, Any]
    indexed_at: str
    missing: bool


def _managed_id(frontmatter: dict[str, Any]) -> str | None:
    if frontmatter.get("managed_by") != _MANAGED_BY:
        return None
    managed_id = frontmatter.get("id")
    return managed_id if isinstance(managed_id, str) else None


class VaultIndexer:
    """Persists the vault index (vault_files) -- see docs/DATABASE_SCHEMA.md #2.

    Read-only with respect to the vault itself (docs/OBSIDIAN_SCHEMA.md
    #13): it only reads and hashes files, never writes to them. Files
    previously indexed but no longer found on disk are marked `missing`,
    never deleted -- see docs/OBSIDIAN_SCHEMA.md #16.
    """

    def __init__(self, engine: Engine, resolver: VaultResolver) -> None:
        self._engine = engine
        self._resolver = resolver

    def reindex(self) -> list[VaultIndexEntry]:
        scan = scan_markdown_files(self._resolver)
        now = datetime.now(UTC).isoformat()
        seen_paths: set[str] = set()
        entries: list[VaultIndexEntry] = []

        with DbSession(self._engine) as db:
            for scanned in scan.files:
                absolute = self._resolver.resolve(scanned.path)
                content = absolute.read_text(encoding="utf-8")
                parsed = parse_frontmatter(content)
                content_hash = hash_content(content)
                modified_at = datetime.fromtimestamp(
                    absolute.stat().st_mtime, tz=UTC
                ).isoformat()
                managed_id = _managed_id(parsed.frontmatter)
                metadata_json = json.dumps(parsed.frontmatter)

                seen_paths.add(scanned.path)
                row = db.get(VaultFileModel, scanned.path)
                if row is None:
                    row = VaultFileModel(path=scanned.path)
                    db.add(row)

                row.content_hash = content_hash
                row.modified_at = modified_at
                row.indexed_at = now
                row.file_type = "markdown"
                row.managed_id = managed_id
                row.metadata_json = metadata_json
                row.missing = False

                entries.append(
                    VaultIndexEntry(
                        path=scanned.path,
                        content_hash=content_hash,
                        file_type="markdown",
                        managed_id=managed_id,
                        metadata=parsed.frontmatter,
                        indexed_at=now,
                        missing=False,
                    )
                )

            for row in db.scalars(select(VaultFileModel)):
                if row.path not in seen_paths and not row.missing:
                    row.missing = True

            db.commit()

        return entries
