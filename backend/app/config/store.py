import json
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from app.config.models import AIProviderConfig, AppConfig
from app.persistence.engine import create_sqlite_engine
from app.persistence.models.config import AIProviderConfigModel, AppSettingModel

_SETTINGS_KEYS = (
    "vault_path",
    "provider_id",
    "model",
    "base_url",
    "language",
    "git_auto_commit",
    "onboarding_step",
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ConfigStore:
    """SQLite-backed store for AppConfig -- app_settings + ai_provider_configs
    (docs/DATABASE_SCHEMA.md #17).

    Formalizes the JSON-file-backed store used during onboarding bootstrap
    (T013) now that the versioned schema exists (T034). The schema itself
    must already be migrated (`alembic upgrade head`) -- this store never
    creates tables itself (docs/AGENTS.md #8: no ad-hoc schema changes at
    application startup).
    """

    def __init__(self, db_path: str) -> None:
        self._engine = create_sqlite_engine(db_path)

    def load(self) -> AppConfig:
        with DbSession(self._engine) as db:
            settings = {
                row.key: json.loads(row.value_json) for row in db.scalars(select(AppSettingModel))
            }
            providers = [
                AIProviderConfig(
                    id=row.id,
                    provider_id=row.provider_id,  # type: ignore[arg-type]
                    model=row.model,
                    base_url=row.base_url,
                    credential_ref=row.credential_ref,
                    enabled=row.enabled,
                    is_default=row.is_default,
                )
                for row in db.scalars(select(AIProviderConfigModel))
            ]

        kwargs = {key: settings[key] for key in _SETTINGS_KEYS if key in settings}
        return AppConfig(ai_providers=providers, **kwargs)

    def save(self, config: AppConfig) -> None:
        now = _now_iso()
        values = {
            "vault_path": config.vault_path,
            "provider_id": config.provider_id,
            "model": config.model,
            "base_url": config.base_url,
            "language": config.language,
            "git_auto_commit": config.git_auto_commit,
            "onboarding_step": config.onboarding_step.value,
        }

        with DbSession(self._engine) as db:
            for key, value in values.items():
                row = db.get(AppSettingModel, key)
                value_json = json.dumps(value)
                if row is None:
                    db.add(AppSettingModel(key=key, value_json=value_json, updated_at=now))
                else:
                    row.value_json = value_json
                    row.updated_at = now

            db.execute(delete(AIProviderConfigModel))
            for provider in config.ai_providers:
                db.add(
                    AIProviderConfigModel(
                        id=provider.id,
                        provider_id=provider.provider_id.value,
                        model=provider.model,
                        base_url=provider.base_url,
                        credential_ref=provider.credential_ref,
                        enabled=provider.enabled,
                        is_default=provider.is_default,
                        created_at=now,
                        updated_at=now,
                    )
                )

            db.commit()
