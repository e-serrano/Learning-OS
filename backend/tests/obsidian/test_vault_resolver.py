from pathlib import Path

import pytest

from app.obsidian.vault_resolver import (
    VaultPathTraversalError,
    VaultResolver,
    VaultUnavailableError,
)


def test_rejects_nonexistent_root(tmp_path: Path) -> None:
    with pytest.raises(VaultUnavailableError):
        VaultResolver(str(tmp_path / "missing"))


def test_rejects_file_as_root(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-dir.txt"
    file_path.write_text("hello")
    with pytest.raises(VaultUnavailableError):
        VaultResolver(str(file_path))


def test_accepts_valid_directory(tmp_path: Path) -> None:
    resolver = VaultResolver(str(tmp_path))
    assert resolver.root == tmp_path.resolve()


def test_resolve_returns_path_inside_root(tmp_path: Path) -> None:
    resolver = VaultResolver(str(tmp_path))
    (tmp_path / "Concepts").mkdir()

    resolved = resolver.resolve("Concepts/note.md")

    assert resolved == (tmp_path / "Concepts" / "note.md").resolve()


def test_resolve_blocks_dotdot_traversal(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    resolver = VaultResolver(str(vault))

    with pytest.raises(VaultPathTraversalError):
        resolver.resolve("../outside.md")


def test_resolve_blocks_deep_dotdot_traversal(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    resolver = VaultResolver(str(vault))

    with pytest.raises(VaultPathTraversalError):
        resolver.resolve("Concepts/../../etc/passwd")


def test_resolve_blocks_absolute_path_injection(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    resolver = VaultResolver(str(vault))

    with pytest.raises(VaultPathTraversalError):
        resolver.resolve("/etc/passwd")


def test_resolve_allows_nested_valid_paths(tmp_path: Path) -> None:
    resolver = VaultResolver(str(tmp_path))
    resolved = resolver.resolve("03_Knowledge/Concepts/Window Functions.md")
    assert resolved.is_relative_to(tmp_path.resolve())
