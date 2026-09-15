from pathlib import Path

from sqlalchemy.orm import Session as DbSession

from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import AIProviderConfigModel, AppSettingModel


def test_app_settings_and_ai_provider_configs_are_registered() -> None:
    assert {"app_settings", "ai_provider_configs"}.issubset(Base.metadata.tables.keys())


def test_app_setting_roundtrips_through_real_sqlite(tmp_path: Path) -> None:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)

    with DbSession(engine) as db:
        db.add(
            AppSettingModel(
                key="vault_path", value_json='"/vault"', updated_at="2026-01-01T00:00:00Z"
            )
        )
        db.commit()

    with DbSession(engine) as db:
        loaded = db.get(AppSettingModel, "vault_path")
        assert loaded is not None
        assert loaded.value_json == '"/vault"'


def test_ai_provider_config_credential_ref_is_only_a_reference(tmp_path: Path) -> None:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)

    with DbSession(engine) as db:
        db.add(
            AIProviderConfigModel(
                id="cfg_1",
                provider_id="openai",
                model="gpt-5",
                credential_ref="openai:abc123",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        db.commit()

    with DbSession(engine) as db:
        loaded = db.get(AIProviderConfigModel, "cfg_1")
        assert loaded is not None
        assert loaded.enabled is True
        assert loaded.is_default is False
        assert loaded.credential_ref == "openai:abc123"


def test_ai_provider_config_has_no_raw_secret_column() -> None:
    columns = {c.name for c in Base.metadata.tables["ai_provider_configs"].columns}
    assert "credential_ref" in columns
    assert "api_key" not in columns
    assert "secret" not in columns
