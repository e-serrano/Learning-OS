import pytest
from pydantic import BaseModel

from app.ai.adapters.mock import MockProvider
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.ai.protocol import AIProvider, AIRequest
from app.ai.retry_policy import RetryingProvider


class Greeting(BaseModel):
    text: str


def _request() -> AIRequest:
    return AIRequest(role="evaluator", prompt_version="evaluator.v1")


def _accepts_provider(provider: AIProvider) -> AIProvider:
    return provider


def test_satisfies_ai_provider_protocol() -> None:
    _accepts_provider(RetryingProvider(MockProvider()))


class _FlakyOnceProvider:
    """Fails validation on the first call, succeeds on the second."""

    def __init__(self, success_response: BaseModel) -> None:
        self._calls = 0
        self._success_response = success_response
        self.seen_requests: list[AIRequest] = []

    async def generate(self, request: AIRequest, response_model: type[BaseModel]) -> BaseModel:
        self.seen_requests.append(request)
        self._calls += 1
        if self._calls == 1:
            raise AIInvalidOutputError("missing required field 'text'")
        return self._success_response


class _AlwaysInvalidProvider:
    async def generate(self, request: AIRequest, response_model: type[BaseModel]) -> BaseModel:
        raise AIInvalidOutputError("always broken")


class _AlwaysUnavailableProvider:
    async def generate(self, request: AIRequest, response_model: type[BaseModel]) -> BaseModel:
        raise AIProviderUnavailableError("connection refused")


@pytest.mark.asyncio
async def test_succeeds_on_first_try_without_retry() -> None:
    primary = MockProvider()
    primary.set_response(Greeting, Greeting(text="hi"))
    retrying = RetryingProvider(primary)

    result = await retrying.generate(_request(), Greeting)

    assert result == Greeting(text="hi")


@pytest.mark.asyncio
async def test_retries_once_after_invalid_output_and_succeeds() -> None:
    flaky = _FlakyOnceProvider(Greeting(text="recovered"))
    retrying = RetryingProvider(flaky)

    result = await retrying.generate(_request(), Greeting)

    assert result == Greeting(text="recovered")
    assert len(flaky.seen_requests) == 2


@pytest.mark.asyncio
async def test_retry_request_carries_the_validation_error() -> None:
    flaky = _FlakyOnceProvider(Greeting(text="recovered"))
    retrying = RetryingProvider(flaky)

    await retrying.generate(_request(), Greeting)

    retry_request = flaky.seen_requests[1]
    assert "previous_validation_error" in retry_request.constraints
    assert "text" in retry_request.constraints["previous_validation_error"]


@pytest.mark.asyncio
async def test_falls_back_when_retry_also_fails_validation() -> None:
    primary = _AlwaysInvalidProvider()
    fallback = MockProvider()
    fallback.set_response(Greeting, Greeting(text="from fallback"))
    retrying = RetryingProvider(primary, fallback=fallback)

    result = await retrying.generate(_request(), Greeting)

    assert result == Greeting(text="from fallback")


@pytest.mark.asyncio
async def test_surfaces_original_failure_when_no_fallback_configured() -> None:
    retrying = RetryingProvider(_AlwaysInvalidProvider())

    with pytest.raises(AIInvalidOutputError, match="always broken"):
        await retrying.generate(_request(), Greeting)


@pytest.mark.asyncio
async def test_surfaces_original_failure_when_fallback_also_fails() -> None:
    retrying = RetryingProvider(_AlwaysInvalidProvider(), fallback=_AlwaysUnavailableProvider())

    with pytest.raises(AIInvalidOutputError, match="always broken"):
        await retrying.generate(_request(), Greeting)


@pytest.mark.asyncio
async def test_network_failure_skips_straight_to_fallback_no_retry() -> None:
    primary = _AlwaysUnavailableProvider()
    fallback = MockProvider()
    fallback.set_response(Greeting, Greeting(text="fallback saved it"))
    retrying = RetryingProvider(primary, fallback=fallback)

    result = await retrying.generate(_request(), Greeting)

    assert result == Greeting(text="fallback saved it")


@pytest.mark.asyncio
async def test_network_failure_without_fallback_surfaces_immediately() -> None:
    retrying = RetryingProvider(_AlwaysUnavailableProvider())

    with pytest.raises(AIProviderUnavailableError, match="connection refused"):
        await retrying.generate(_request(), Greeting)


@pytest.mark.asyncio
async def test_invalid_output_never_returns_an_unvalidated_result() -> None:
    """Every path either returns a schema-valid response_model instance or raises."""
    retrying = RetryingProvider(_AlwaysInvalidProvider())
    try:
        await retrying.generate(_request(), Greeting)
        raised = False
    except AIInvalidOutputError:
        raised = True
    assert raised
