import pytest

from app.config.models import OnboardingStep
from app.onboarding.state_machine import (
    ONBOARDING_SEQUENCE,
    InvalidOnboardingTransitionError,
    is_complete,
    next_step,
    validate_transition,
)


def test_sequence_matches_spec_order() -> None:
    assert ONBOARDING_SEQUENCE == [
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


@pytest.mark.parametrize(
    "current,expected",
    [
        (OnboardingStep.WELCOME, OnboardingStep.VAULT),
        (OnboardingStep.VAULT, OnboardingStep.VAULT_SCAN),
        (OnboardingStep.VAULT_SCAN, OnboardingStep.AI_PROVIDER),
        (OnboardingStep.AI_PROVIDER, OnboardingStep.CREDENTIAL),
        (OnboardingStep.CREDENTIAL, OnboardingStep.MODEL),
        (OnboardingStep.MODEL, OnboardingStep.VALIDATE),
        (OnboardingStep.VALIDATE, OnboardingStep.FIRST_GOAL),
        (OnboardingStep.FIRST_GOAL, OnboardingStep.COMPLETE),
    ],
)
def test_next_step_follows_canonical_order(
    current: OnboardingStep, expected: OnboardingStep
) -> None:
    assert next_step(current) == expected


def test_next_step_after_complete_is_none() -> None:
    assert next_step(OnboardingStep.COMPLETE) is None


def test_validate_transition_accepts_the_immediate_next_step() -> None:
    validate_transition(OnboardingStep.WELCOME, OnboardingStep.VAULT)  # must not raise


def test_validate_transition_rejects_skipping_steps() -> None:
    with pytest.raises(InvalidOnboardingTransitionError):
        validate_transition(OnboardingStep.WELCOME, OnboardingStep.AI_PROVIDER)


def test_validate_transition_rejects_going_backward() -> None:
    with pytest.raises(InvalidOnboardingTransitionError):
        validate_transition(OnboardingStep.MODEL, OnboardingStep.VAULT)


def test_validate_transition_rejects_staying_in_place() -> None:
    with pytest.raises(InvalidOnboardingTransitionError):
        validate_transition(OnboardingStep.VAULT, OnboardingStep.VAULT)


def test_validate_transition_rejects_advancing_past_complete() -> None:
    with pytest.raises(InvalidOnboardingTransitionError):
        validate_transition(OnboardingStep.COMPLETE, OnboardingStep.WELCOME)


def test_is_complete_only_true_at_complete_step() -> None:
    assert is_complete(OnboardingStep.COMPLETE) is True
    for step in ONBOARDING_SEQUENCE:
        if step != OnboardingStep.COMPLETE:
            assert is_complete(step) is False
