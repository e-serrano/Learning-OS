import pytest

from app.ai.adapters.mock import MockProvider
from app.ai.adapters.mock_scenarios import (
    evaluation_invalid_output,
    evaluation_partial,
    evaluation_provider_unavailable,
    evaluation_success,
    evaluation_with_misconceptions,
    progress_overconfident,
    progress_underconfident,
    progress_well_calibrated,
)
from app.ai.contracts import EvaluatorResponse, ProgressResponse
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.ai.protocol import AIRequest


def _request() -> AIRequest:
    return AIRequest(role="evaluator", prompt_version="evaluator.v1")


def test_evaluation_success_is_fully_correct() -> None:
    result = evaluation_success()
    assert result.correctness == 1.0
    assert result.misconceptions == []


def test_evaluation_partial_is_between_zero_and_one() -> None:
    result = evaluation_partial()
    assert 0 < result.correctness < 1


def test_evaluation_with_misconceptions_has_default_misconception() -> None:
    result = evaluation_with_misconceptions()
    assert len(result.misconceptions) == 1


def test_evaluation_with_misconceptions_accepts_custom_list() -> None:
    result = evaluation_with_misconceptions(["Off-by-one in ROW_NUMBER"])
    assert result.misconceptions == ["Off-by-one in ROW_NUMBER"]


def test_scenarios_are_deterministic_across_calls() -> None:
    assert evaluation_success() == evaluation_success()
    assert evaluation_partial() == evaluation_partial()


def test_progress_overconfident_has_higher_overconfidence() -> None:
    result = progress_overconfident()
    assert result.calibration.overconfidence > result.calibration.underconfidence


def test_progress_underconfident_has_higher_underconfidence() -> None:
    result = progress_underconfident()
    assert result.calibration.underconfidence > result.calibration.overconfidence


def test_progress_well_calibrated_has_low_values_both_ways() -> None:
    result = progress_well_calibrated()
    assert result.calibration.overconfidence < 0.2
    assert result.calibration.underconfidence < 0.2


def test_error_factories_produce_the_right_exception_types() -> None:
    assert isinstance(evaluation_provider_unavailable(), AIProviderUnavailableError)
    assert isinstance(evaluation_invalid_output(), AIInvalidOutputError)


@pytest.mark.asyncio
async def test_scenarios_plug_directly_into_mock_provider() -> None:
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, evaluation_with_misconceptions())

    result = await provider.generate(_request(), EvaluatorResponse)

    assert isinstance(result, EvaluatorResponse)
    assert result.misconceptions


@pytest.mark.asyncio
async def test_error_scenario_plugs_into_mock_provider_set_error() -> None:
    provider = MockProvider()
    provider.set_response(EvaluatorResponse, evaluation_success())
    provider.set_error(evaluation_provider_unavailable())

    with pytest.raises(AIProviderUnavailableError):
        await provider.generate(_request(), EvaluatorResponse)


@pytest.mark.asyncio
async def test_progress_scenario_plugs_into_mock_provider() -> None:
    provider = MockProvider()
    provider.set_response(ProgressResponse, progress_overconfident())

    result = await provider.generate(_request(), ProgressResponse)

    assert isinstance(result, ProgressResponse)
    assert result.calibration.overconfidence > 0.5
