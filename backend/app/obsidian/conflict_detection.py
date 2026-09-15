from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.obsidian.hashing import hash_content
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.models import VaultFileModel


class VaultConflictError(Exception):
    """The file changed externally since Learning OS last indexed it.

    Maps to API_SPEC.md's VAULT_CONFLICT error code -- see
    docs/OBSIDIAN_SCHEMA.md #12: "Do not overwrite. Reload and regenerate
    the proposed change."
    """

    def __init__(self, path: str) -> None:
        super().__init__(f"Vault file changed since Learning OS last read it: {path}")
        self.path = path


def assert_no_conflict(engine: Engine, resolver: VaultResolver, path: str) -> None:
    """Raise VaultConflictError if the file's current hash != its indexed hash.

    A path with no indexed row is not a conflict -- it's either a new file
    being created, or one the vault index hasn't seen yet.
    """
    with DbSession(engine) as db:
        indexed = db.get(VaultFileModel, path)

    if indexed is None:
        return

    absolute = resolver.resolve(path)
    if not absolute.exists():
        raise VaultConflictError(path)

    current_hash = hash_content(absolute.read_text(encoding="utf-8"))
    if current_hash != indexed.content_hash:
        raise VaultConflictError(path)
