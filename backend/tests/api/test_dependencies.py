import subprocess
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.dependencies import _build_curation_trigger, get_vault_resolver, is_vault_a_git_repo
from app.config.models import AppConfig


class FakeConfigStore:
    def __init__(self, vault_path: str | None) -> None:
        self._vault_path = vault_path

    def load(self) -> AppConfig:
        return AppConfig(vault_path=self._vault_path)


def test_get_vault_resolver_raises_when_unconfigured() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_vault_resolver(FakeConfigStore(vault_path=None))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "VAULT_UNAVAILABLE"


def test_get_vault_resolver_raises_when_path_does_not_exist(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"

    with pytest.raises(HTTPException) as exc_info:
        get_vault_resolver(FakeConfigStore(vault_path=str(missing)))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "VAULT_UNAVAILABLE"


def test_get_vault_resolver_returns_resolver_for_valid_path(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()

    resolver = get_vault_resolver(FakeConfigStore(vault_path=str(vault)))

    assert resolver.root == vault.resolve()


class FakeConfigStoreForCuration:
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def load(self) -> AppConfig:
        return self._config


def test_build_curation_trigger_returns_none_when_vault_not_configured() -> None:
    store = FakeConfigStoreForCuration(AppConfig(vault_path=None))

    result = _build_curation_trigger(store)  # type: ignore[arg-type]

    assert result is None


def test_build_curation_trigger_returns_none_when_no_ai_provider_is_configured(
    tmp_path: Path,
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    store = FakeConfigStoreForCuration(AppConfig(vault_path=str(vault), ai_providers=[]))

    result = _build_curation_trigger(store)  # type: ignore[arg-type]

    assert result is None


def test_is_vault_a_git_repo_false_when_vault_not_configured() -> None:
    store = FakeConfigStoreForCuration(AppConfig(vault_path=None))

    assert is_vault_a_git_repo(store) is False  # type: ignore[arg-type]


def test_is_vault_a_git_repo_false_for_a_plain_vault(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    store = FakeConfigStoreForCuration(AppConfig(vault_path=str(vault)))

    assert is_vault_a_git_repo(store) is False  # type: ignore[arg-type]


def test_is_vault_a_git_repo_true_for_a_real_git_repo(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    subprocess.run(["git", "init"], cwd=vault, capture_output=True, check=True)
    store = FakeConfigStoreForCuration(AppConfig(vault_path=str(vault)))

    assert is_vault_a_git_repo(store) is True  # type: ignore[arg-type]
