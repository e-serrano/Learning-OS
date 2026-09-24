from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_config_store
from app.config.store import ConfigStore
from app.main import app
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "test.sqlite3"
    Base.metadata.create_all(create_sqlite_engine(str(db_path)))

    app.dependency_overrides[get_config_store] = lambda: ConfigStore(str(db_path))
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def test_get_settings_defaults_to_english(client: TestClient) -> None:
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "en"
    assert body["supported_languages"]["es"] == "Spanish"


def test_update_language_persists_the_new_value(client: TestClient) -> None:
    response = client.patch("/api/v1/settings/language", json={"language": "es"})
    assert response.status_code == 200
    assert response.json()["language"] == "es"

    assert client.get("/api/v1/settings").json()["language"] == "es"


def test_update_language_rejects_an_unsupported_code(client: TestClient) -> None:
    response = client.patch("/api/v1/settings/language", json={"language": "klingon"})
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "VALIDATION_ERROR"
