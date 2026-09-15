from app.config.models import OnboardingStep

ONBOARDING_SEQUENCE: list[OnboardingStep] = [
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
"""Canonical order -- see docs/SPECS.md #20 and docs/CONFIGURATION.md."""


class InvalidOnboardingTransitionError(ValueError):
    def __init__(self, current: OnboardingStep, target: OnboardingStep) -> None:
        super().__init__(f"Cannot transition onboarding from {current} to {target}")
        self.current = current
        self.target = target


def next_step(current: OnboardingStep) -> OnboardingStep | None:
    """The only step reachable from `current`, or None once COMPLETE."""
    index = ONBOARDING_SEQUENCE.index(current)
    if index == len(ONBOARDING_SEQUENCE) - 1:
        return None
    return ONBOARDING_SEQUENCE[index + 1]


def validate_transition(current: OnboardingStep, target: OnboardingStep) -> None:
    """Onboarding is strictly linear and forward-only -- no skipping steps.

    Reconfiguring vault/provider after COMPLETE (docs/SPECS.md #20) is a
    separate concern handled by application services, not this state
    machine.
    """
    if target != next_step(current):
        raise InvalidOnboardingTransitionError(current, target)


def is_complete(step: OnboardingStep) -> bool:
    return step == OnboardingStep.COMPLETE
