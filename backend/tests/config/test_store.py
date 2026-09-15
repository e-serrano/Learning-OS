from pathlib import Path

import pytest

from app.ai.provider_registry import ProviderId
from app.config.models import AIProviderConfig, AppConfig, OnboardingStep
from app.config.store import ConfigStore
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.sqlite3"
    Base.metadata.create_all(create_sqlite_engine(str(path)))
    return path


def test_load_empty_database_returns_defaults(db_path: Path) -> None:
    store = ConfigStore(str(db_path))
    assert store.load() == AppConfig()


def test_save_then_load_roundtrips(db_path: Path) -> None:
    store = ConfigStore(str(db_path))
    original = AppConfig(
        vault_path="/home/user/vault",
        provider_id="ollama",
        model="llama3",
        language="es",
        onboarding_step=OnboardingStep.VAULT_SCAN,
    )
    store.save(original)

    loaded = store.load()
    assert loaded == original


def test_save_then_load_roundtrips_ai_providers(db_path: Path) -> None:
    store = ConfigStore(str(db_path))
    original = AppConfig(
        ai_providers=[
            AIProviderConfig(
                provider_id=ProviderId.OPENAI,
                model="gpt-5",
                credential_ref="openai:abc123",
                is_default=True,
            ),
        ]
    )
    store.save(original)

    loaded = store.load()
    assert loaded == original
    assert loaded.ai_providers[0].credential_ref == "openai:abc123"


def test_save_overwrites_previous_content(db_path: Path) -> None:
    store = ConfigStore(str(db_path))
    store.save(AppConfig(language="en"))
    store.save(AppConfig(language="fr"))

    assert store.load().language == "fr"


def test_save_replaces_ai_providers_rather_than_accumulating(db_path: Path) -> None:
    store = ConfigStore(str(db_path))
    store.save(
        AppConfig(
            ai_providers=[AIProviderConfig(provider_id=ProviderId.MOCK, model="mock-1")]
        )
    )
    store.save(
        AppConfig(
            ai_providers=[AIProviderConfig(provider_id=ProviderId.OLLAMA, model="llama3")]
        )
    )

    loaded = store.load()
    assert len(loaded.ai_providers) == 1
    assert loaded.ai_providers[0].provider_id == ProviderId.OLLAMA


def test_credential_ref_is_the_only_secret_related_field_persisted(db_path: Path) -> None:
    """The store only ever writes credential_ref, never a raw secret."""
    store = ConfigStore(str(db_path))
    store.save(
        AppConfig(
            ai_providers=[
                AIProviderConfig(
                    provider_id=ProviderId.OPENAI,
                    model="gpt-5",
                    credential_ref="openai:ref-only",
                )
            ]
        )
    )

    raw = db_path.read_bytes()
    wal_path = db_path.with_name(db_path.name + "-wal")
    if wal_path.exists():
        raw += wal_path.read_bytes()

    assert b"openai:ref-only" in raw
    assert b"sk-" not in raw
