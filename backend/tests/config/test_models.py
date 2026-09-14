from app.config.models import AppConfig, OnboardingStep


def test_default_app_config_starts_at_welcome() -> None:
    config = AppConfig()
    assert config.onboarding_step == OnboardingStep.WELCOME
    assert config.vault_path is None
    assert config.language == "en"


def test_app_config_has_no_credential_field() -> None:
    assert "credential" not in AppConfig.model_fields
    assert "api_key" not in AppConfig.model_fields


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
