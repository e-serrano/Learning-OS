import hashlib
from pathlib import Path


def hash_content(content: str) -> str:
    """SHA-256 of note content (UTF-8), used for the vault index and
    conflict detection -- see docs/DATABASE_SCHEMA.md #2 (vault_files)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def hash_file(path: Path) -> str:
    return hash_content(path.read_text(encoding="utf-8"))
