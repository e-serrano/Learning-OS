from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.dependencies import get_vault_resolver
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
