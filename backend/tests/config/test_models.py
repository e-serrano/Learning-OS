import pytest

from app.ai.provider_registry import ProviderId
from app.config.models import AIProviderConfig, AppConfig, OnboardingStep


def test_default_app_config_starts_at_welcome() -> None:
    config = AppConfig()
    assert config.onboarding_step == OnboardingStep.WELCOME
    assert config.vault_path is None
    assert config.language == "es"


def test_app_config_has_no_credential_field() -> None:
    assert "credential" not in AppConfig.model_fields
    assert "api_key" not in AppConfig.model_fields


def test_ai_provider_config_has_no_raw_secret_field() -> None:
    assert "credential_ref" in AIProviderConfig.model_fields
    assert "api_key" not in AIProviderConfig.model_fields
    assert "secret" not in AIProviderConfig.model_fields


def test_ai_provider_config_defaults() -> None:
    config = AIProviderConfig(provider_id=ProviderId.OLLAMA, model="llama3")
    assert config.enabled is True
    assert config.is_default is False
    assert config.credential_ref is None
    assert config.id  # generated


def test_ai_provider_config_ids_are_unique() -> None:
    a = AIProviderConfig(provider_id=ProviderId.MOCK, model="mock-1")
    b = AIProviderConfig(provider_id=ProviderId.MOCK, model="mock-1")
    assert a.id != b.id


def test_app_config_accepts_multiple_providers_with_one_default() -> None:
    config = AppConfig(
        ai_providers=[
            AIProviderConfig(provider_id=ProviderId.MOCK, model="mock-1", is_default=True),
            AIProviderConfig(provider_id=ProviderId.OLLAMA, model="llama3", is_default=False),
        ]
    )
    assert len(config.ai_providers) == 2


def test_app_config_rejects_more_than_one_default_provider() -> None:
    with pytest.raises(ValueError, match="At most one"):
        AppConfig(
            ai_providers=[
                AIProviderConfig(provider_id=ProviderId.MOCK, model="mock-1", is_default=True),
                AIProviderConfig(provider_id=ProviderId.OLLAMA, model="llama3", is_default=True),
            ]
        )


def test_onboarding_step_sequence_matches_spec() -> None:
    assert list(OnboardingStep) == [
        OnboardingStep.WELCOME,
        OnboardingStep.VAULT,
        OnboardingStep.VAULT_SCAN,
        OnboardingStep.AI_PROVIDER,
        OnboardingStep.CREDENTIAL,
        OnboardingStep.MODEL,
        OnboardingStep.VALIDATE,
        OnboardingStep.FIRST_GOAL,
        OnboardingStep.COMPLETE,
    ]
