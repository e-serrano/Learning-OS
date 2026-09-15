import json

import httpx
import pytest
from pydantic import BaseModel

from app.ai.adapters._openai_compatible_base import OpenAICompatibleAdapter
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.ai.protocol import AIProvider, AIRequest


class Greeting(BaseModel):
    text: str


def _request() -> AIRequest:
    return AIRequest(role="tutor", prompt_version="tutor.v1")


def _accepts_provider(provider: AIProvider) -> AIProvider:
    return provider


def _chat_completion_response(content: dict) -> httpx.Response:  # type: ignore[type-arg]
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": json.dumps(content)}}]},
    )


@pytest.mark.asyncio
async def test_satisfies_ai_provider_protocol() -> None:
    _accepts_provider(OpenAICompatibleAdapter(model="gpt-5", base_url="https://api.example.com"))


@pytest.mark.asyncio
async def test_successful_call_returns_parsed_response() -> None:
    transport = httpx.MockTransport(lambda req: _chat_completion_response({"text": "hi"}))
    client = httpx.AsyncClient(transport=transport)
    adapter = OpenAICompatibleAdapter(
        model="gpt-5", base_url="https://api.example.com/v1", api_key="sk-test", client=client
    )

    result = await adapter.generate(_request(), Greeting)

    assert result == Greeting(text="hi")


@pytest.mark.asyncio
async def test_request_includes_auth_header_and_correct_url() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        return _chat_completion_response({"text": "hi"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleAdapter(
        model="gpt-5", base_url="https://api.example.com/v1", api_key="sk-test", client=client
    )

    await adapter.generate(_request(), Greeting)

    assert captured["url"] == "https://api.example.com/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-test"


@pytest.mark.asyncio
async def test_request_omits_auth_header_when_no_api_key() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        return _chat_completion_response({"text": "hi"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleAdapter(
        model="local-model", base_url="http://localhost:8080/v1", client=client
    )

    await adapter.generate(_request(), Greeting)

    assert captured["auth"] is None


@pytest.mark.asyncio
async def test_request_payload_includes_json_schema_response_format() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return _chat_completion_response({"text": "hi"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleAdapter(
        model="gpt-5", base_url="https://api.example.com/v1", api_key="k", client=client
    )

    await adapter.generate(_request(), Greeting)

    body = captured["body"]
    assert body["model"] == "gpt-5"
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["name"] == "Greeting"
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_http_error_raises_provider_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server error"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleAdapter(
        model="gpt-5", base_url="https://api.example.com/v1", api_key="k", client=client
    )

    with pytest.raises(AIProviderUnavailableError):
        await adapter.generate(_request(), Greeting)


@pytest.mark.asyncio
async def test_malformed_json_content_raises_invalid_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "not valid json {{"}}]}
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleAdapter(
        model="gpt-5", base_url="https://api.example.com/v1", api_key="k", client=client
    )

    with pytest.raises(AIInvalidOutputError):
        await adapter.generate(_request(), Greeting)


@pytest.mark.asyncio
async def test_missing_choices_key_raises_invalid_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleAdapter(
        model="gpt-5", base_url="https://api.example.com/v1", api_key="k", client=client
    )

    with pytest.raises(AIInvalidOutputError):
        await adapter.generate(_request(), Greeting)


@pytest.mark.asyncio
async def test_response_schema_mismatch_raises_invalid_output() -> None:
    """Content is valid JSON but doesn't satisfy the requested schema."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _chat_completion_response({"wrong_field": 123})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleAdapter(
        model="gpt-5", base_url="https://api.example.com/v1", api_key="k", client=client
    )

    with pytest.raises(AIInvalidOutputError):
        await adapter.generate(_request(), Greeting)
