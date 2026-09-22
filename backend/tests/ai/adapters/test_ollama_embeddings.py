import json

import httpx
import pytest

from app.ai.adapters.ollama_embeddings import OllamaEmbeddingProvider
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError


@pytest.mark.asyncio
async def test_successful_call_returns_vectors() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"embeddings": [[0.1, 0.2], [0.3, 0.4]]})
    )
    client = httpx.AsyncClient(transport=transport)
    provider = OllamaEmbeddingProvider(model="nomic-embed-text", client=client)

    result = await provider.embed(["first", "second"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]


@pytest.mark.asyncio
async def test_request_hits_the_native_embed_endpoint_with_model_and_input() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"embeddings": [[0.1]]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OllamaEmbeddingProvider(
        model="nomic-embed-text", base_url="http://localhost:11434", client=client
    )

    await provider.embed(["only text"])

    assert captured["url"] == "http://localhost:11434/api/embed"
    assert captured["body"] == {"model": "nomic-embed-text", "input": ["only text"]}


@pytest.mark.asyncio
async def test_http_error_raises_provider_unavailable() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(500, json={"error": "down"}))
    )
    provider = OllamaEmbeddingProvider(model="m", client=client)

    with pytest.raises(AIProviderUnavailableError):
        await provider.embed(["text"])


@pytest.mark.asyncio
async def test_missing_embeddings_key_raises_invalid_output() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"unexpected": True}))
    )
    provider = OllamaEmbeddingProvider(model="m", client=client)

    with pytest.raises(AIInvalidOutputError):
        await provider.embed(["text"])


@pytest.mark.asyncio
async def test_vector_count_mismatch_raises_invalid_output() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"embeddings": [[0.1]]}))
    )
    provider = OllamaEmbeddingProvider(model="m", client=client)

    with pytest.raises(AIInvalidOutputError):
        await provider.embed(["first", "second"])
