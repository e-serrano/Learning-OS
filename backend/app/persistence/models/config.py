from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class AppSettingModel(Base):
    """Non-secret settings only -- see docs/DATABASE_SCHEMA.md #17."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(primary_key=True)
    value_json: Mapped[str]
    updated_at: Mapped[str]


class AIProviderConfigModel(Base):
    """credential_ref is only a keyring identifier, never the secret itself."""

    __tablename__ = "ai_provider_configs"

    id: Mapped[str] = mapped_column(primary_key=True)
    provider_id: Mapped[str]
    model: Mapped[str]
    base_url: Mapped[str | None]
    credential_ref: Mapped[str | None]
    fallback_model: Mapped[str | None]
    enabled: Mapped[bool] = mapped_column(default=True)
    is_default: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str]
    updated_at: Mapped[str]
