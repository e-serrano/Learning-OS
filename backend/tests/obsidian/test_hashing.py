from pathlib import Path

from app.obsidian.hashing import hash_content, hash_file


def test_hash_content_is_sha256_hex() -> None:
    digest = hash_content("hello")
    assert digest == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert len(digest) == 64


def test_hash_content_is_deterministic() -> None:
    assert hash_content("same text") == hash_content("same text")


def test_hash_content_differs_for_different_content() -> None:
    assert hash_content("a") != hash_content("b")


def test_hash_content_is_sensitive_to_whitespace() -> None:
    assert hash_content("text") != hash_content("text\n")


def test_hash_file_matches_hash_content(tmp_path: Path) -> None:
    file_path = tmp_path / "note.md"
    file_path.write_text("# Note\n\nBody.\n")

    assert hash_file(file_path) == hash_content("# Note\n\nBody.\n")


def test_hash_file_changes_when_file_content_changes(tmp_path: Path) -> None:
    file_path = tmp_path / "note.md"
    file_path.write_text("v1")
    first = hash_file(file_path)

    file_path.write_text("v2")
    second = hash_file(file_path)

    assert first != second
