from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.ai.adapters.mock_embeddings import MockEmbeddingProvider
from app.ai.embedding_orchestrator import EmbeddingOrchestrator
from app.ai.errors import AIProviderUnavailableError
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import AIRunModel


class _AlwaysDownProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise AIProviderUnavailableError("simulated outage")


def _engine(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


@pytest.mark.asyncio
async def test_successful_call_returns_vectors_and_logs_ai_run(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    orchestrator = EmbeddingOrchestrator(
        engine, MockEmbeddingProvider(), provider_name="mock", model="mock-embed"
    )

    result = await orchestrator.embed(["hello", "world"])

    assert len(result) == 2
    with DbSession(engine) as db:
        runs = list(db.scalars(select(AIRunModel)))
        assert len(runs) == 1
        assert runs[0].success is True
        assert runs[0].role == "embedding"
        assert runs[0].provider == "mock"
        assert runs[0].model == "mock-embed"
        assert runs[0].output_schema == "Embedding"


@pytest.mark.asyncio
async def test_failed_call_still_logs_ai_run_and_reraises(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    orchestrator = EmbeddingOrchestrator(
        engine, _AlwaysDownProvider(), provider_name="mock", model="mock-embed"
    )

    with pytest.raises(AIProviderUnavailableError):
        await orchestrator.embed(["text"])

    with DbSession(engine) as db:
        runs = list(db.scalars(select(AIRunModel)))
        assert len(runs) == 1
        assert runs[0].success is False
        assert runs[0].error_type == "AIProviderUnavailableError"


@pytest.mark.asyncio
async def test_empty_input_returns_empty_list_without_logging_a_run(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    orchestrator = EmbeddingOrchestrator(
        engine, MockEmbeddingProvider(), provider_name="mock", model="mock-embed"
    )

    result = await orchestrator.embed([])

    assert result == []
    with DbSession(engine) as db:
        assert list(db.scalars(select(AIRunModel))) == []


@pytest.mark.asyncio
async def test_ai_run_never_stores_raw_text_content(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    orchestrator = EmbeddingOrchestrator(
        engine, MockEmbeddingProvider(), provider_name="mock", model="mock-embed"
    )

    await orchestrator.embed(["secret-looking-content-xyz"])

    with DbSession(engine) as db:
        run = db.scalars(select(AIRunModel)).first()
        assert run is not None
        assert "secret-looking-content-xyz" not in (run.input_hash or "")
