from pathlib import Path

import keyring.errors
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_config_store, get_credential_store
from app.config.credentials import CredentialStore
from app.config.store import ConfigStore
from app.main import app
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine


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
    db_path = tmp_path / "test.sqlite3"
    Base.metadata.create_all(create_sqlite_engine(str(db_path)))

    app.dependency_overrides[get_config_store] = lambda: ConfigStore(str(db_path))
    app.dependency_overrides[get_credential_store] = lambda: CredentialStore(backend=fake_keyring)
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
    response = client.post("/api/v1/onboarding/vault", json={"path": str(tmp_path / "missing")})
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "VAULT_UNAVAILABLE"


def test_configure_ai_provider_requires_vault_first(client: TestClient) -> None:
    response = client.post(
        "/api/v1/onboarding/ai-provider",
        json={"provider_id": "mock", "model": "mock-1"},
    )
    assert response.status_code == 409
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
    client.post("/api/v1/onboarding/ai-provider", json={"provider_id": "mock", "model": "mock-1"})

    response = client.post("/api/v1/onboarding/ai-provider/validate", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["onboarding_step"] == "VALIDATE"


def test_validate_ollama_local_provider_passes_structural_check_but_fails_live(
    client: TestClient, vault_dir: Path
) -> None:
    """Structurally well-formed (base_url present, no credential needed --
    see test_capability_check.py's own unit test for that in isolation),
    but nothing is actually listening at that base_url in a test run --
    docs/TASKS.md T145's whole point is that this must now be caught here,
    not only much later when a real generation call is attempted."""
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post(
        "/api/v1/onboarding/ai-provider",
        json={"provider_id": "ollama", "model": "llama3", "base_url": "http://localhost:11434"},
    )

    response = client.post("/api/v1/onboarding/ai-provider/validate", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["onboarding_step"] == "AI_PROVIDER"  # never advanced past this


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


def test_validate_provider_with_credential_succeeds_and_never_leaks_secret(
    client: TestClient, vault_dir: Path
) -> None:
    """`mock`, not a remote provider: this is about the storage/response
    path (a successfully-validated credential is stored via the keyring
    and never echoed back), not about any one provider's live wire
    protocol (T145 makes a real remote provider's "validate" genuinely
    hit the network, which a real credential like "sk-super-secret-value"
    would never actually pass)."""
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post(
        "/api/v1/onboarding/ai-provider",
        json={"provider_id": "mock", "model": "mock-1"},
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
    assert response.status_code == 409
    assert response.json()["detail"]["error"]["code"] == "SESSION_STATE_ERROR"


def test_full_happy_path_reaches_complete_with_mock_provider(
    client: TestClient, vault_dir: Path
) -> None:
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post("/api/v1/onboarding/ai-provider", json={"provider_id": "mock", "model": "mock-1"})
    client.post("/api/v1/onboarding/ai-provider/validate", json={})

    response = client.post("/api/v1/onboarding/complete")

    assert response.status_code == 200
    assert response.json()["onboarding_step"] == "COMPLETE"

    status = client.get("/api/v1/onboarding/status")
    assert status.json()["onboarding_step"] == "COMPLETE"


def test_complete_stays_blocked_when_the_local_provider_never_actually_validated(
    client: TestClient, vault_dir: Path
) -> None:
    """A structurally-fine-looking ollama config (base_url present, no
    credential needed) that nothing is listening behind must not be able
    to reach onboarding COMPLETE -- docs/TASKS.md T145's real point: a
    config that only ever *looked* valid can no longer silently finish
    onboarding."""
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post(
        "/api/v1/onboarding/ai-provider",
        json={"provider_id": "ollama", "model": "llama3", "base_url": "http://localhost:11434"},
    )
    client.post("/api/v1/onboarding/ai-provider/validate", json={})

    response = client.post("/api/v1/onboarding/complete")

    assert response.status_code == 409
    assert response.json()["detail"]["error"]["code"] == "SESSION_STATE_ERROR"


def test_a_fake_credential_against_a_real_remote_provider_fails_live_and_is_never_stored(
    client: TestClient, vault_dir: Path
) -> None:
    """Before T145, a made-up credential like this would have been
    accepted (`check_provider_capability` only checked it was non-empty)
    and onboarding would have reached COMPLETE with a provider that was
    never actually reachable -- exactly this task's motivating bug."""
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post(
        "/api/v1/onboarding/ai-provider", json={"provider_id": "anthropic", "model": "claude-x"}
    )
    validate = client.post(
        "/api/v1/onboarding/ai-provider/validate", json={"credential": "sk-ant-simulated"}
    )
    assert validate.json()["ok"] is False

    response = client.post("/api/v1/onboarding/complete")
    assert response.status_code == 409

    status = client.get("/api/v1/onboarding/status")
    assert "sk-ant-simulated" not in status.text
    assert status.json()["ai_providers"] == []  # never stored -- validation never succeeded


def test_fallback_model_is_saved_alongside_the_primary_provider(
    client: TestClient, vault_dir: Path
) -> None:
    """docs/TASKS.md T148, user request: a second model (e.g. OpenRouter's
    `openrouter/free` auto-router) saved as the configured provider's
    fallback -- tried by RetryingProvider if the primary model errors out
    or is rate-limited. Only the primary model is live-validated (T145);
    the fallback is trusted as-is, same as `base_url`."""
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post(
        "/api/v1/onboarding/ai-provider",
        json={
            "provider_id": "mock",
            "model": "mock-1",
            "fallback_model": "mock-2",
        },
    )

    response = client.post("/api/v1/onboarding/ai-provider/validate", json={})
    assert response.status_code == 200
    assert response.json()["ok"] is True

    status = client.get("/api/v1/onboarding/status")
    provider = status.json()["ai_providers"][0]
    assert provider["fallback_model"] == "mock-2"


def test_fallback_model_is_optional(client: TestClient, vault_dir: Path) -> None:
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post("/api/v1/onboarding/ai-provider", json={"provider_id": "mock", "model": "mock-1"})
    client.post("/api/v1/onboarding/ai-provider/validate", json={})

    status = client.get("/api/v1/onboarding/status")
    assert status.json()["ai_providers"][0]["fallback_model"] is None


def test_complete_is_idempotent_once_already_complete(client: TestClient, vault_dir: Path) -> None:
    client.post("/api/v1/onboarding/vault", json={"path": str(vault_dir)})
    client.post("/api/v1/onboarding/ai-provider", json={"provider_id": "mock", "model": "mock-1"})
    client.post("/api/v1/onboarding/ai-provider/validate", json={})
    client.post("/api/v1/onboarding/complete")

    response = client.post("/api/v1/onboarding/complete")

    assert response.status_code == 200
    assert response.json()["onboarding_step"] == "COMPLETE"
