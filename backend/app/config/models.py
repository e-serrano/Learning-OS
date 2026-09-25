from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from app.ai.provider_registry import ProviderId


class OnboardingStep(StrEnum):
    WELCOME = "WELCOME"
    VAULT = "VAULT"
    VAULT_SCAN = "VAULT_SCAN"
    AI_PROVIDER = "AI_PROVIDER"
    CREDENTIAL = "CREDENTIAL"
    MODEL = "MODEL"
    VALIDATE = "VALIDATE"
    FIRST_GOAL = "FIRST_GOAL"
    COMPLETE = "COMPLETE"


class AIProviderConfig(BaseModel):
    """A saved provider configuration -- mirrors the `ai_provider_configs` table.

    `credential_ref` is only a keyring lookup key, never the secret itself
    -- see docs/DATABASE_SCHEMA.md #17 and docs/AGENTS.md #21.
    """

    id: str = Field(default_factory=lambda: uuid4().hex)
    provider_id: ProviderId
    model: str
    base_url: str | None = None
    credential_ref: str | None = None
    enabled: bool = True
    is_default: bool = False
    fallback_model: str | None = None
    """Same provider/credential/base_url, different model -- tried once by
    `RetryingProvider` (app/ai/provider_factory.py) if `model` errors out
    or is rate-limited. Never validated at save time (docs/TASKS.md T148):
    only `model` goes through `check_provider_capability`/
    `validate_provider_connection` (T145) -- checking two models on every
    onboarding/Settings save would double that call's cost and latency for
    a model that may never actually get used."""


class AppConfig(BaseModel):
    """Non-secret, user-configurable local settings.

    Persisted by ConfigStore. Never holds credential values -- see
    docs/AGENTS.md #21 and docs/AI_CONTRACTS.md #18.
    """

    vault_path: str | None = None
    provider_id: str | None = None
    model: str | None = None
    base_url: str | None = None
    fallback_model: str | None = None
    language: str = "es"
    git_auto_commit: bool = False
    onboarding_step: OnboardingStep = OnboardingStep.WELCOME
    ai_providers: list[AIProviderConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def _at_most_one_default_provider(self) -> "AppConfig":
        defaults = [p for p in self.ai_providers if p.is_default]
        if len(defaults) > 1:
            raise ValueError("At most one AIProviderConfig may have is_default=True")
        return self
