import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.obsidian.conflict_detection import assert_no_conflict
from app.obsidian.hashing import hash_content
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.models import VaultFileModel


class AtomicWriteVerificationError(Exception):
    """Re-read content after the atomic replace didn't match what was written."""


def write_note(engine: Engine, resolver: VaultResolver, path: str, content: str) -> str:
    """Atomically write `content` to `path` inside the vault.

    Follows docs/OBSIDIAN_SCHEMA.md #10-11: checks for an external conflict
    first, writes via a temp file in the same directory and os.replace
    (never truncates the original before the new content is validated),
    re-reads to verify the write landed correctly, and updates the vault
    index. Returns the new content hash.
    """
    assert_no_conflict(engine, resolver, path)

    target = resolver.resolve(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise

    reread = target.read_text(encoding="utf-8")
    if reread != content:
        raise AtomicWriteVerificationError(f"Re-read content did not match for {path!r}")

    new_hash = hash_content(reread)
    now = datetime.now(UTC).isoformat()
    modified_at = datetime.fromtimestamp(target.stat().st_mtime, tz=UTC).isoformat()

    with DbSession(engine) as db:
        row = db.get(VaultFileModel, path)
        if row is None:
            row = VaultFileModel(
                path=path, file_type="markdown", metadata_json="{}", missing=False
            )
            db.add(row)
        row.content_hash = new_hash
        row.modified_at = modified_at
        row.indexed_at = now
        row.missing = False
        db.commit()

    return new_hash
