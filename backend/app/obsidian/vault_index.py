import json
import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session as DbSession

from app.obsidian.frontmatter import ParsedFrontmatter, parse_frontmatter
from app.obsidian.hashing import hash_content
from app.obsidian.markdown_scanner import scan_markdown_files
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.models import VAULT_SEARCH_FTS_TABLE, VaultFileModel

_MANAGED_BY = "learning_os"
_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _derive_title(path: str, parsed: ParsedFrontmatter) -> str:
    """Best-effort display title for a search result (docs/TASKS.md T127)
    -- there is no dedicated title field anywhere in the domain model, so
    this mirrors how a human would actually identify the note: its own
    `title` frontmatter if set, else its first Markdown heading, else its
    filename."""
    frontmatter_title = parsed.frontmatter.get("title")
    if isinstance(frontmatter_title, str) and frontmatter_title.strip():
        return frontmatter_title.strip()

    heading = _HEADING_RE.search(parsed.body)
    if heading is not None:
        return heading.group(1).strip()

    return path.rsplit("/", 1)[-1].removesuffix(".md")


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

    Also rebuilds `vault_files_fts` (docs/TASKS.md T127) on every call --
    it already reads each file's full content here to hash it, so this is
    the one place a full-text search index can stay current at no extra
    I/O cost. Unlike `vault_files`, a missing file's FTS row is deleted
    outright rather than flagged: search is a derived view of *current*
    content, not an audit trail, so surfacing a result for a note that no
    longer exists would be actively misleading.
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
                modified_at = datetime.fromtimestamp(absolute.stat().st_mtime, tz=UTC).isoformat()
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

                db.execute(
                    text(f"DELETE FROM {VAULT_SEARCH_FTS_TABLE} WHERE path = :path"),
                    {"path": scanned.path},
                )
                db.execute(
                    text(
                        f"INSERT INTO {VAULT_SEARCH_FTS_TABLE}(path, title, body) "
                        "VALUES (:path, :title, :body)"
                    ),
                    {
                        "path": scanned.path,
                        "title": _derive_title(scanned.path, parsed),
                        "body": parsed.body,
                    },
                )

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
                    db.execute(
                        text(f"DELETE FROM {VAULT_SEARCH_FTS_TABLE} WHERE path = :path"),
                        {"path": row.path},
                    )

            db.commit()

        return entries
