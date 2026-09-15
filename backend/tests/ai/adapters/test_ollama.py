import json

import httpx
import pytest
from pydantic import BaseModel

from app.ai.adapters.ollama import OllamaProvider
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.ai.protocol import AIRequest


class Greeting(BaseModel):
    text: str


def _request() -> AIRequest:
    return AIRequest(role="tutor", prompt_version="tutor.v1")


@pytest.mark.asyncio
async def test_successful_call_returns_parsed_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": json.dumps({"text": "hi"})}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OllamaProvider(model="llama3", client=client)

    result = await provider.generate(_request(), Greeting)

    assert result == Greeting(text="hi")


@pytest.mark.asyncio
async def test_request_hits_native_chat_endpoint_with_format_schema() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": json.dumps({"text": "hi"})}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OllamaProvider(model="llama3", base_url="http://localhost:11434", client=client)

    await provider.generate(_request(), Greeting)

    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["body"]["model"] == "llama3"
    assert captured["body"]["format"] == Greeting.model_json_schema()
    assert captured["body"]["stream"] is False


@pytest.mark.asyncio
async def test_connection_error_raises_provider_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OllamaProvider(model="llama3", client=client)

    with pytest.raises(AIProviderUnavailableError):
        await provider.generate(_request(), Greeting)


@pytest.mark.asyncio
async def test_malformed_response_raises_invalid_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OllamaProvider(model="llama3", client=client)

    with pytest.raises(AIInvalidOutputError):
        await provider.generate(_request(), Greeting)
