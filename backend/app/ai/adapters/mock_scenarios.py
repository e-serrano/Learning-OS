"""Deterministic scenario factories for MockProvider.

T017 built the generic mock; this adds named, reusable scenarios so
downstream tests (and later services) don't hand-roll response objects --
see docs/AGENTS.md #17 and T050's acceptance: success, error, partial
credit, misconceptions, confidence calibration.
"""

from app.ai.contracts import CalibrationBreakdown, EvaluatorResponse, ProgressResponse
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError


def evaluation_success() -> EvaluatorResponse:
    """A fully correct, independent, well-reasoned attempt."""
    return EvaluatorResponse(
        correctness=1.0,
        reasoning=1.0,
        completeness=1.0,
        independence=1.0,
        transfer=1.0,
        misconceptions=[],
        feedback="Correct and well-reasoned.",
        recommended_action="advance",
    )


def evaluation_partial() -> EvaluatorResponse:
    """Right idea, incomplete or imperfect execution."""
    return EvaluatorResponse(
        correctness=0.6,
        reasoning=0.5,
        completeness=0.4,
        independence=0.7,
        transfer=0.3,
        misconceptions=[],
        feedback="Partially correct; missing edge cases.",
        recommended_action="practice_more",
    )


def evaluation_with_misconceptions(misconceptions: list[str] | None = None) -> EvaluatorResponse:
    """Incorrect, with specific identified misconceptions -- see
    docs/DOMAIN_MODEL.md #10 (recurring mistakes must affect selection)."""
    return EvaluatorResponse(
        correctness=0.2,
        reasoning=0.3,
        completeness=0.5,
        independence=0.5,
        transfer=0.1,
        misconceptions=misconceptions or ["Confuses ROW_NUMBER and RANK"],
        feedback="A common misconception was detected.",
        recommended_action="review_concept",
    )


def evaluation_provider_unavailable() -> AIProviderUnavailableError:
    return AIProviderUnavailableError("Simulated provider outage")


def evaluation_invalid_output() -> AIInvalidOutputError:
    return AIInvalidOutputError("Simulated malformed structured output")


def progress_overconfident() -> ProgressResponse:
    """Reports high confidence but performs poorly."""
    return ProgressResponse(
        progress_summary="Overconfident on several concepts.",
        weak=["concept_1"],
        calibration=CalibrationBreakdown(overconfidence=0.7, underconfidence=0.1),
    )


def progress_underconfident() -> ProgressResponse:
    """Underestimates their own ability relative to actual performance."""
    return ProgressResponse(
        progress_summary="Underestimates their own ability.",
        mastered=["concept_1"],
        calibration=CalibrationBreakdown(overconfidence=0.1, underconfidence=0.6),
    )


def progress_well_calibrated() -> ProgressResponse:
    return ProgressResponse(
        progress_summary="Confidence matches performance well.",
        calibration=CalibrationBreakdown(overconfidence=0.1, underconfidence=0.1),
    )
