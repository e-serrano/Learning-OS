import pytest
from pydantic import BaseModel

from app.ai.adapters.mock import MockProvider
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.ai.protocol import AIRequest


class Greeting(BaseModel):
    text: str


class Farewell(BaseModel):
    text: str


def make_request(role: str = "tutor") -> AIRequest:
    return AIRequest(role=role, prompt_version="tutor.v1")


@pytest.mark.asyncio
async def test_returns_configured_static_response() -> None:
    provider = MockProvider()
    provider.set_response(Greeting, Greeting(text="hello"))

    result = await provider.generate(make_request(), Greeting)

    assert result == Greeting(text="hello")


@pytest.mark.asyncio
async def test_returns_configured_factory_response_using_request() -> None:
    provider = MockProvider()
    provider.set_response(Greeting, lambda req: Greeting(text=f"hello {req.role}"))

    result = await provider.generate(make_request(role="learner"), Greeting)

    assert result == Greeting(text="hello learner")


@pytest.mark.asyncio
async def test_raises_when_no_response_configured_for_model() -> None:
    provider = MockProvider()

    with pytest.raises(AIInvalidOutputError):
        await provider.generate(make_request(), Greeting)


@pytest.mark.asyncio
async def test_responses_are_scoped_per_response_model() -> None:
    provider = MockProvider()
    provider.set_response(Greeting, Greeting(text="hi"))

    with pytest.raises(AIInvalidOutputError):
        await provider.generate(make_request(), Farewell)


@pytest.mark.asyncio
async def test_set_error_makes_generate_raise_it() -> None:
    provider = MockProvider()
    provider.set_response(Greeting, Greeting(text="hi"))
    provider.set_error(AIProviderUnavailableError("simulated outage"))

    with pytest.raises(AIProviderUnavailableError):
        await provider.generate(make_request(), Greeting)


@pytest.mark.asyncio
async def test_clear_error_restores_normal_responses() -> None:
    provider = MockProvider()
    provider.set_response(Greeting, Greeting(text="hi"))
    provider.set_error(AIProviderUnavailableError("simulated outage"))
    provider.clear_error()

    result = await provider.generate(make_request(), Greeting)

    assert result == Greeting(text="hi")


@pytest.mark.asyncio
async def test_never_makes_network_calls_is_deterministic_across_runs() -> None:
    provider = MockProvider()
    provider.set_response(Greeting, Greeting(text="stable"))

    first = await provider.generate(make_request(), Greeting)
    second = await provider.generate(make_request(), Greeting)

    assert first == second == Greeting(text="stable")
