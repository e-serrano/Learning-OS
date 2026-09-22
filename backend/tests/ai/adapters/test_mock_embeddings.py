import pytest

from app.ai.adapters.mock_embeddings import MockEmbeddingProvider


@pytest.mark.asyncio
async def test_embed_returns_one_vector_per_text() -> None:
    provider = MockEmbeddingProvider()

    vectors = await provider.embed(["hello", "world", "third text"])

    assert len(vectors) == 3


@pytest.mark.asyncio
async def test_embed_is_deterministic_for_the_same_text() -> None:
    provider = MockEmbeddingProvider()

    first = await provider.embed(["stable text"])
    second = await provider.embed(["stable text"])

    assert first == second


@pytest.mark.asyncio
async def test_embed_differs_for_different_text() -> None:
    provider = MockEmbeddingProvider()

    vectors = await provider.embed(["text one", "text two"])

    assert vectors[0] != vectors[1]


@pytest.mark.asyncio
async def test_embed_respects_the_configured_dimensionality() -> None:
    provider = MockEmbeddingProvider(dims=8)

    vectors = await provider.embed(["some text"])

    assert len(vectors[0]) == 8


@pytest.mark.asyncio
async def test_embed_values_are_within_a_bounded_range() -> None:
    provider = MockEmbeddingProvider()

    vectors = await provider.embed(["some text"])

    assert all(-1.0 <= value <= 1.0 for value in vectors[0])


@pytest.mark.asyncio
async def test_embed_empty_list_returns_empty_list() -> None:
    provider = MockEmbeddingProvider()

    assert await provider.embed([]) == []
