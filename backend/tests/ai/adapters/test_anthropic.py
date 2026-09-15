import json

import httpx
import pytest
from pydantic import BaseModel

from app.ai.adapters.anthropic import AnthropicProvider
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.ai.protocol import AIRequest


class Greeting(BaseModel):
    text: str


def _request() -> AIRequest:
    return AIRequest(role="tutor", prompt_version="tutor.v1")


def _tool_use_response(input_data: dict) -> httpx.Response:  # type: ignore[type-arg]
    return httpx.Response(
        200,
        json={"content": [{"type": "tool_use", "name": "respond", "input": input_data}]},
    )


@pytest.mark.asyncio
async def test_successful_call_returns_parsed_response() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: _tool_use_response({"text": "hi"}))
    )
    provider = AnthropicProvider(model="claude-opus-5", api_key="sk-ant-test", client=client)

    result = await provider.generate(_request(), Greeting)

    assert result == Greeting(text="hi")


@pytest.mark.asyncio
async def test_request_uses_native_headers_and_forced_tool_choice() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content)
        return _tool_use_response({"text": "hi"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = AnthropicProvider(model="claude-opus-5", api_key="sk-ant-test", client=client)

    await provider.generate(_request(), Greeting)

    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "sk-ant-test"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert "authorization" not in captured["headers"]  # Anthropic uses x-api-key, not Bearer
    body = captured["body"]
    assert body["tool_choice"] == {"type": "tool", "name": "respond"}
    assert body["tools"][0]["input_schema"] == Greeting.model_json_schema()


@pytest.mark.asyncio
async def test_http_error_raises_provider_unavailable() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(401, json={"error": "bad key"}))
    )
    provider = AnthropicProvider(model="claude-opus-5", api_key="wrong-key", client=client)

    with pytest.raises(AIProviderUnavailableError):
        await provider.generate(_request(), Greeting)


@pytest.mark.asyncio
async def test_response_without_tool_use_block_raises_invalid_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": [{"type": "text", "text": "not a tool call"}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = AnthropicProvider(model="claude-opus-5", api_key="sk-ant-test", client=client)

    with pytest.raises(AIInvalidOutputError):
        await provider.generate(_request(), Greeting)


@pytest.mark.asyncio
async def test_tool_input_not_matching_schema_raises_invalid_output() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: _tool_use_response({"wrong_field": 1}))
    )
    provider = AnthropicProvider(model="claude-opus-5", api_key="sk-ant-test", client=client)

    with pytest.raises(AIInvalidOutputError):
        await provider.generate(_request(), Greeting)
