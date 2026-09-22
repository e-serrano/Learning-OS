import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from app.ai.adapters.mock_embeddings import MockEmbeddingProvider
from app.ai.embedding_orchestrator import EmbeddingOrchestrator
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import VAULT_SEARCH_FTS_TABLE
from app.services.semantic_search_service import InvalidSearchQueryError, SemanticSearchService

NOW = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
MOCK_DIMS = 32


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _store_embedding(
    engine: Engine, path: str, vector: list[float], model: str = "mock-embed"
) -> None:
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO vault_embeddings(path, content_hash, model, dims, "
                "vector_json, created_at) VALUES (:path, 'h', :model, :dims, :vec, :now)"
            ),
            {
                "path": path,
                "model": model,
                "dims": len(vector),
                "vec": json.dumps(vector),
                "now": NOW,
            },
        )
        conn.commit()


def _index_title(engine: Engine, path: str, title: str) -> None:
    with engine.connect() as conn:
        conn.execute(
            text(
                f"INSERT INTO {VAULT_SEARCH_FTS_TABLE}(path, title, body) "
                "VALUES (:path, :title, '')"
            ),
            {"path": path, "title": title},
        )
        conn.commit()


def _service(engine: Engine, provider: object = None) -> SemanticSearchService:
    orchestrator = EmbeddingOrchestrator(
        engine, provider or MockEmbeddingProvider(), provider_name="mock", model="mock-embed"
    )
    return SemanticSearchService(engine, orchestrator)  # type: ignore[arg-type]


def _vec(dims: int = MOCK_DIMS, fill: float = 0.5) -> list[float]:
    return [fill] * dims


@pytest.mark.asyncio
async def test_search_rejects_a_blank_query(engine: Engine) -> None:
    service = _service(engine)

    with pytest.raises(InvalidSearchQueryError):
        await service.search("   ")


@pytest.mark.asyncio
async def test_search_returns_empty_list_when_no_embeddings_exist(engine: Engine) -> None:
    service = _service(engine)

    assert await service.search("anything") == []


@pytest.mark.asyncio
async def test_search_ranks_the_closest_vector_first(engine: Engine) -> None:
    """A fixed query vector should rank an identical stored vector above an
    orthogonal one."""

    class FixedProvider:
        async def embed(self, texts: list[str]) -> list[list[float]]:
            return [[1.0, 0.0, 0.0]]

    _store_embedding(engine, "close.md", [1.0, 0.0, 0.0])
    _store_embedding(engine, "far.md", [0.0, 1.0, 0.0])
    _index_title(engine, "close.md", "Close Note")
    _index_title(engine, "far.md", "Far Note")
    service = _service(engine, FixedProvider())

    results = await service.search("query")

    assert results[0].path == "close.md"
    assert results[0].title == "Close Note"
    assert results[0].score > results[1].score


@pytest.mark.asyncio
async def test_search_excludes_vectors_from_a_different_model(engine: Engine) -> None:
    _store_embedding(engine, "stale.md", _vec(dims=2), model="old-model")
    service = _service(engine)

    assert await service.search("anything") == []


@pytest.mark.asyncio
async def test_search_skips_a_dimension_mismatched_row_instead_of_crashing(
    engine: Engine,
) -> None:
    """Same model name but a different vector length (e.g. the provider was
    reconfigured under the same model string) must never crash the whole
    search -- the row is excluded, not fatal."""
    _store_embedding(engine, "mismatched.md", _vec(dims=4))
    _store_embedding(engine, "ok.md", _vec(dims=MOCK_DIMS))
    service = _service(engine)

    results = await service.search("anything")

    assert [r.path for r in results] == ["ok.md"]


@pytest.mark.asyncio
async def test_search_falls_back_to_path_when_no_title_is_indexed(engine: Engine) -> None:
    _store_embedding(engine, "untitled.md", _vec())
    service = _service(engine)

    results = await service.search("anything")

    assert results[0].title == "untitled.md"


@pytest.mark.asyncio
async def test_search_respects_the_limit(engine: Engine) -> None:
    for i in range(5):
        _store_embedding(engine, f"note_{i}.md", _vec(fill=float(i)))
    service = _service(engine)

    results = await service.search("anything", limit=2)

    assert len(results) == 2
