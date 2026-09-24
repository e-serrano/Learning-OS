import subprocess
from pathlib import Path

import pytest

from app.obsidian.vault_resolver import VaultResolver
from app.services.vault_git_service import VaultGitService


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        capture_output=True,
        check=True,
    )


@pytest.fixture
def git_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    _init_git_repo(vault)
    return vault


def test_is_git_repo_true_for_an_initialized_repo(git_vault: Path) -> None:
    service = VaultGitService(VaultResolver(str(git_vault)))
    assert service.is_git_repo() is True


def test_is_git_repo_false_for_a_plain_directory(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    service = VaultGitService(VaultResolver(str(plain)))
    assert service.is_git_repo() is False


def test_commit_file_creates_a_commit_for_the_given_file(git_vault: Path) -> None:
    (git_vault / "note.md").write_text("hello\n", encoding="utf-8")
    service = VaultGitService(VaultResolver(str(git_vault)))

    committed = service.commit_file("note.md", "Learning OS: create_file note.md")

    assert committed is True
    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=git_vault, capture_output=True, text=True, check=True
    ).stdout
    assert "Learning OS: create_file note.md" in log


def test_commit_file_only_stages_the_named_file(git_vault: Path) -> None:
    (git_vault / "note.md").write_text("hello\n", encoding="utf-8")
    (git_vault / "other.md").write_text("untouched\n", encoding="utf-8")
    service = VaultGitService(VaultResolver(str(git_vault)))

    service.commit_file("note.md", "commit note only")

    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=git_vault, capture_output=True, text=True, check=True
    ).stdout
    assert "?? other.md" in status
    assert "note.md" not in status  # committed, so it no longer shows as dirty/untracked


def test_commit_file_returns_false_when_nothing_changed(git_vault: Path) -> None:
    (git_vault / "note.md").write_text("hello\n", encoding="utf-8")
    service = VaultGitService(VaultResolver(str(git_vault)))
    assert service.commit_file("note.md", "first commit") is True

    # same content, nothing new to commit
    second = service.commit_file("note.md", "second commit attempt")

    assert second is False


def test_commit_file_returns_false_when_not_a_git_repo(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "note.md").write_text("hello\n", encoding="utf-8")
    service = VaultGitService(VaultResolver(str(plain)))

    assert service.commit_file("note.md", "message") is False


def test_is_git_repo_false_when_git_binary_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError("git not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    plain = tmp_path / "plain"
    plain.mkdir()
    service = VaultGitService(VaultResolver(str(plain)))

    assert service.is_git_repo() is False
