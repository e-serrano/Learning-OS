from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_config_store
from app.config.models import AIProviderConfig
from app.config.store import ConfigStore
from app.main import app
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine


@pytest.fixture
def config_store(tmp_path: Path) -> ConfigStore:
    db_path = tmp_path / "config.sqlite3"
    Base.metadata.create_all(create_sqlite_engine(str(db_path)))
    return ConfigStore(str(db_path))


@pytest.fixture
def client(config_store: ConfigStore) -> TestClient:
    app.dependency_overrides[get_config_store] = lambda: config_store
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def test_list_supported_providers_includes_mock(client: TestClient) -> None:
    response = client.get("/api/v1/providers")

    assert response.status_code == 200
    ids = {p["id"] for p in response.json()}
    assert "mock" in ids
    assert "openai" in ids


def test_list_supported_providers_never_mentions_credentials(client: TestClient) -> None:
    response = client.get("/api/v1/providers")

    body_text = response.text.lower()
    assert "api_key" not in body_text or "requires_api_key" in body_text
    assert "credential" not in body_text


def test_get_provider_config_defaults_to_empty(client: TestClient) -> None:
    response = client.get("/api/v1/providers/config")

    assert response.status_code == 200
    body = response.json()
    assert body["provider_id"] is None
    assert body["ai_providers"] == []


def test_get_provider_config_never_returns_credential_ref(
    client: TestClient, config_store: ConfigStore
) -> None:
    config = config_store.load()
    config.provider_id = "openai"
    config.model = "gpt-5"
    config.ai_providers = [
        AIProviderConfig(
            provider_id="openai",  # type: ignore[arg-type]
            model="gpt-5",
            credential_ref="cred_ref_abc123",
            is_default=True,
        )
    ]
    config_store.save(config)

    response = client.get("/api/v1/providers/config")

    assert response.status_code == 200
    assert "credential_ref" not in response.text
    assert "cred_ref_abc123" not in response.text
    body = response.json()
    assert body["ai_providers"][0]["provider_id"] == "openai"
    assert body["ai_providers"][0]["is_default"] is True


def test_validate_provider_ok_for_mock(client: TestClient) -> None:
    response = client.post(
        "/api/v1/providers/validate", json={"provider_id": "mock", "model": "mock-1"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["provider_id"] == "mock"


def test_validate_provider_fails_without_required_credential(client: TestClient) -> None:
    response = client.post(
        "/api/v1/providers/validate", json={"provider_id": "openai", "model": "gpt-5"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert "credential" in (body["reason"] or "").lower()


def test_validate_provider_never_echoes_credential(client: TestClient) -> None:
    response = client.post(
        "/api/v1/providers/validate",
        json={"provider_id": "openai", "model": "gpt-5", "credential": "sk-super-secret"},
    )

    assert "sk-super-secret" not in response.text
