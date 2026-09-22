import json

import httpx
import pytest

from app.ai.adapters._openai_compatible_embeddings_base import OpenAICompatibleEmbeddingAdapter
from app.ai.embedding_protocol import EmbeddingProvider
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError


def _accepts_provider(provider: EmbeddingProvider) -> EmbeddingProvider:
    return provider


def _embeddings_response(vectors: list[list[float]]) -> httpx.Response:
    return httpx.Response(
        200,
        json={"data": [{"embedding": v, "index": i} for i, v in enumerate(vectors)]},
    )


@pytest.mark.asyncio
async def test_satisfies_embedding_provider_protocol() -> None:
    _accepts_provider(
        OpenAICompatibleEmbeddingAdapter(
            model="text-embedding-3-small", base_url="https://api.example.com"
        )
    )


@pytest.mark.asyncio
async def test_successful_call_returns_vectors_in_order() -> None:
    transport = httpx.MockTransport(lambda req: _embeddings_response([[0.1, 0.2], [0.3, 0.4]]))
    client = httpx.AsyncClient(transport=transport)
    adapter = OpenAICompatibleEmbeddingAdapter(
        model="text-embedding-3-small",
        base_url="https://api.example.com/v1",
        api_key="sk-test",
        client=client,
    )

    result = await adapter.embed(["first", "second"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]


@pytest.mark.asyncio
async def test_reorders_by_index_when_provider_returns_out_of_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {"embedding": [9.0], "index": 1},
                    {"embedding": [1.0], "index": 0},
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleEmbeddingAdapter(
        model="m", base_url="https://api.example.com/v1", api_key="k", client=client
    )

    result = await adapter.embed(["a", "b"])

    assert result == [[1.0], [9.0]]


@pytest.mark.asyncio
async def test_request_includes_auth_header_correct_url_and_input() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return _embeddings_response([[0.1]])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleEmbeddingAdapter(
        model="text-embedding-3-small",
        base_url="https://api.example.com/v1",
        api_key="sk-test",
        client=client,
    )

    await adapter.embed(["only text"])

    assert captured["url"] == "https://api.example.com/v1/embeddings"
    assert captured["auth"] == "Bearer sk-test"
    assert captured["body"] == {"model": "text-embedding-3-small", "input": ["only text"]}


@pytest.mark.asyncio
async def test_request_omits_auth_header_when_no_api_key() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        return _embeddings_response([[0.1]])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleEmbeddingAdapter(
        model="local-model", base_url="http://localhost:8080/v1", client=client
    )

    await adapter.embed(["text"])

    assert captured["auth"] is None


@pytest.mark.asyncio
async def test_http_error_raises_provider_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server error"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleEmbeddingAdapter(
        model="m", base_url="https://api.example.com/v1", api_key="k", client=client
    )

    with pytest.raises(AIProviderUnavailableError):
        await adapter.embed(["text"])


@pytest.mark.asyncio
async def test_missing_data_key_raises_invalid_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleEmbeddingAdapter(
        model="m", base_url="https://api.example.com/v1", api_key="k", client=client
    )

    with pytest.raises(AIInvalidOutputError):
        await adapter.embed(["text"])


@pytest.mark.asyncio
async def test_vector_count_mismatch_raises_invalid_output() -> None:
    """Asked for 2 embeddings, provider only returned 1 -- must never
    silently return a shorter/misaligned list."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _embeddings_response([[0.1]])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleEmbeddingAdapter(
        model="m", base_url="https://api.example.com/v1", api_key="k", client=client
    )

    with pytest.raises(AIInvalidOutputError):
        await adapter.embed(["first", "second"])
