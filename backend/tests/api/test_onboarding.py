from pathlib import Path

import keyring.errors
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_config_store, get_credential_store
from app.config.credentials import CredentialStore
from app.config.store import ConfigStore
from app.main import app


class FakeKeyringBackend:
    def __init__(self) -> None:
        self._data: dict[tuple[str, str], str] = {}

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self._data[(service_name, username)] = password

    def get_password(self, service_name: str, username: str) -> str | None:
        return self._data.get((service_name, username))

    def delete_password(self, service_name: str, username: str) -> None:
        key = (service_name, username)
        if key not in self._data:
            raise keyring.errors.PasswordDeleteError("not found")
        del self._data[key]


@pytest.fixture
def fake_keyring() -> FakeKeyringBackend:
    return FakeKeyringBackend()


@pytest.fixture
def client(tmp_path: Path, fake_keyring: FakeKeyringBackend) -> TestClient:
    app.dependency_overrides[get_config_store] = lambda: ConfigStore(
        tmp_path / "app_config.json"
    )
    app.dependency_overrides[get_credential_store] = lambda: CredentialStore(
        backend=fake_keyring
    )
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "note.md").write_text("# Note")
    return vault


def test_status_defaults_to_welcome(client: TestClient) -> None:
    response = client.get("/api/v1/onboarding/status")
    assert response.status_code == 200
    assert response.json()["onboarding_step"] == "WELCOME"
    assert response.json()["vault_path"] is None


def test_configure_vault_advances_to_vault_scan(client: TestClient, vault_dir: Path) -> None:
    response = client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    assert response.status_code == 200
    body = response.json()
    assert body["onboarding_step"] == "VAULT_SCAN"
    assert body["scan"]["markdown_file_count"] == 1


def test_configure_vault_rejects_nonexistent_path(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/api/v1/onboarding/vault", json={"path": str(tmp_path / "missing")}
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "VAULT_UNAVAILABLE"


def test_configure_ai_provider_requires_vault_first(client: TestClient) -> None:
    response = client.post(
        "/api/v1/onboarding/ai-provider",
        json={"provider_id": "mock", "model": "mock-1"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "SESSION_STATE_ERROR"


def test_configure_ai_provider_advances_state(client: TestClient, vault_dir: Path) -> None:
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})

    response = client.post(
        "/api/v1/onboarding/ai-provider",
        json={"provider_id": "mock", "model": "mock-1"},
    )

    assert response.status_code == 200
    assert response.json()["onboarding_step"] == "AI_PROVIDER"


def test_validate_mock_provider_succeeds_without_credential(
    client: TestClient, vault_dir: Path
) -> None:
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post(
        "/api/v1/onboarding/ai-provider", json={"provider_id": "mock", "model": "mock-1"}
    )

    response = client.post("/api/v1/onboarding/ai-provider/validate", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["onboarding_step"] == "VALIDATE"


def test_validate_ollama_local_provider_requires_base_url_but_no_credential(
    client: TestClient, vault_dir: Path
) -> None:
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post(
        "/api/v1/onboarding/ai-provider",
        json={"provider_id": "ollama", "model": "llama3", "base_url": "http://localhost:11434"},
    )

    response = client.post("/api/v1/onboarding/ai-provider/validate", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["onboarding_step"] == "VALIDATE"


def test_validate_remote_provider_without_credential_fails_and_does_not_advance(
    client: TestClient, vault_dir: Path
) -> None:
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post(
        "/api/v1/onboarding/ai-provider",
        json={"provider_id": "openai", "model": "gpt-5"},
    )

    response = client.post("/api/v1/onboarding/ai-provider/validate", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["reason"] == "Missing required API credential"
    assert body["onboarding_step"] == "AI_PROVIDER"


def test_validate_remote_provider_with_credential_succeeds_and_never_leaks_secret(
    client: TestClient, vault_dir: Path
) -> None:
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post(
        "/api/v1/onboarding/ai-provider",
        json={"provider_id": "openai", "model": "gpt-5"},
    )

    response = client.post(
        "/api/v1/onboarding/ai-provider/validate",
        json={"credential": "sk-super-secret-value"},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "sk-super-secret-value" not in response.text

    status = client.get("/api/v1/onboarding/status")
    assert "sk-super-secret-value" not in status.text
    provider = status.json()["ai_providers"][0]
    assert provider["credential_ref"] is not None
    assert provider["is_default"] is True


def test_complete_requires_vault_and_validated_provider(client: TestClient) -> None:
    response = client.post("/api/v1/onboarding/complete")
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "SESSION_STATE_ERROR"


def test_full_happy_path_reaches_complete_with_mock_provider(
    client: TestClient, vault_dir: Path
) -> None:
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post(
        "/api/v1/onboarding/ai-provider", json={"provider_id": "mock", "model": "mock-1"}
    )
    client.post("/api/v1/onboarding/ai-provider/validate", json={})

    response = client.post("/api/v1/onboarding/complete")

    assert response.status_code == 200
    assert response.json()["onboarding_step"] == "COMPLETE"

    status = client.get("/api/v1/onboarding/status")
    assert status.json()["onboarding_step"] == "COMPLETE"


def test_full_happy_path_reaches_complete_with_ollama_local_provider(
    client: TestClient, vault_dir: Path
) -> None:
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post(
        "/api/v1/onboarding/ai-provider",
        json={"provider_id": "ollama", "model": "llama3", "base_url": "http://localhost:11434"},
    )
    client.post("/api/v1/onboarding/ai-provider/validate", json={})

    response = client.post("/api/v1/onboarding/complete")

    assert response.status_code == 200
    assert response.json()["onboarding_step"] == "COMPLETE"


def test_full_happy_path_reaches_complete_with_simulated_remote_provider(
    client: TestClient, vault_dir: Path
) -> None:
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post(
        "/api/v1/onboarding/ai-provider", json={"provider_id": "anthropic", "model": "claude-x"}
    )
    validate = client.post(
        "/api/v1/onboarding/ai-provider/validate", json={"credential": "sk-ant-simulated"}
    )
    assert validate.json()["ok"] is True

    response = client.post("/api/v1/onboarding/complete")

    assert response.status_code == 200
    assert response.json()["onboarding_step"] == "COMPLETE"

    status = client.get("/api/v1/onboarding/status")
    assert "sk-ant-simulated" not in status.text
    assert status.json()["ai_providers"][0]["credential_ref"].startswith("anthropic:")


def test_complete_is_idempotent_once_already_complete(
    client: TestClient, vault_dir: Path
) -> None:
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post(
        "/api/v1/onboarding/ai-provider", json={"provider_id": "mock", "model": "mock-1"}
    )
    client.post("/api/v1/onboarding/ai-provider/validate", json={})
    client.post("/api/v1/onboarding/complete")

    response = client.post("/api/v1/onboarding/complete")

    assert response.status_code == 200
    assert response.json()["onboarding_step"] == "COMPLETE"
