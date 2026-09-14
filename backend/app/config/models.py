from enum import StrEnum

from pydantic import BaseModel


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


class AppConfig(BaseModel):
    """Non-secret, user-configurable local settings.

    Persisted by ConfigStore. Never holds credential values -- see
    docs/AGENTS.md #21 and docs/AI_CONTRACTS.md #18.
    """

    vault_path: str | None = None
    provider_id: str | None = None
    model: str | None = None
    base_url: str | None = None
    language: str = "en"
    onboarding_step: OnboardingStep = OnboardingStep.WELCOME
