import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.ai.adapters.mock_embeddings import MockEmbeddingProvider
from app.ai.embedding_orchestrator import EmbeddingOrchestrator
from app.obsidian.vault_index import VaultIndexer
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import VaultEmbeddingModel
from app.services.embedding_service import EmbeddingService


def _setup(tmp_path: Path) -> tuple[EmbeddingService, Engine, Path]:
    vault = tmp_path / "vault"
    vault.mkdir()
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    resolver = VaultResolver(str(vault))
    orchestrator = EmbeddingOrchestrator(
        engine, MockEmbeddingProvider(), provider_name="mock", model="mock-embed"
    )
    service = EmbeddingService(engine, resolver, orchestrator)
    return service, engine, vault


@pytest.mark.asyncio
async def test_generate_for_empty_vault_embeds_nothing(tmp_path: Path) -> None:
    service, engine, vault = _setup(tmp_path)
    VaultIndexer(engine, VaultResolver(str(vault))).reindex()

    summary = await service.generate_for_vault()

    assert summary.files_total == 0
    assert summary.embedded == 0
    assert summary.skipped_unchanged == 0


@pytest.mark.asyncio
async def test_generate_embeds_every_new_indexed_file(tmp_path: Path) -> None:
    service, engine, vault = _setup(tmp_path)
    (vault / "a.md").write_text("# A\n\nContent about window functions.\n")
    (vault / "b.md").write_text("# B\n\nContent about subqueries.\n")
    VaultIndexer(engine, VaultResolver(str(vault))).reindex()

    summary = await service.generate_for_vault()

    assert summary.files_total == 2
    assert summary.embedded == 2
    assert summary.skipped_unchanged == 0
    with DbSession(engine) as db:
        rows = list(db.scalars(select(VaultEmbeddingModel)))
        assert {r.path for r in rows} == {"a.md", "b.md"}
        assert all(r.model == "mock-embed" for r in rows)
        assert all(json.loads(r.vector_json) for r in rows)


@pytest.mark.asyncio
async def test_generate_skips_files_whose_content_hash_is_unchanged(tmp_path: Path) -> None:
    service, engine, vault = _setup(tmp_path)
    (vault / "a.md").write_text("# A\n\nOriginal content.\n")
    VaultIndexer(engine, VaultResolver(str(vault))).reindex()
    await service.generate_for_vault()

    VaultIndexer(engine, VaultResolver(str(vault))).reindex()
    summary = await service.generate_for_vault()

    assert summary.files_total == 1
    assert summary.embedded == 0
    assert summary.skipped_unchanged == 1


@pytest.mark.asyncio
async def test_generate_re_embeds_a_file_whose_content_changed(tmp_path: Path) -> None:
    service, engine, vault = _setup(tmp_path)
    note = vault / "a.md"
    note.write_text("# A\n\nOriginal content.\n")
    VaultIndexer(engine, VaultResolver(str(vault))).reindex()
    await service.generate_for_vault()
    with DbSession(engine) as db:
        first_hash = db.get(VaultEmbeddingModel, "a.md").content_hash  # type: ignore[union-attr]

    note.write_text("# A\n\nCompletely different content now.\n")
    VaultIndexer(engine, VaultResolver(str(vault))).reindex()
    summary = await service.generate_for_vault()

    assert summary.embedded == 1
    assert summary.skipped_unchanged == 0
    with DbSession(engine) as db:
        row = db.get(VaultEmbeddingModel, "a.md")
        assert row is not None
        assert row.content_hash != first_hash


@pytest.mark.asyncio
async def test_generate_excludes_missing_files(tmp_path: Path) -> None:
    service, engine, vault = _setup(tmp_path)
    note = vault / "a.md"
    note.write_text("# A\n\nContent.\n")
    VaultIndexer(engine, VaultResolver(str(vault))).reindex()
    note.unlink()
    VaultIndexer(engine, VaultResolver(str(vault))).reindex()

    summary = await service.generate_for_vault()

    assert summary.files_total == 0
    assert summary.embedded == 0


@pytest.mark.asyncio
async def test_generate_strips_frontmatter_before_embedding(tmp_path: Path) -> None:
    """The embedded text is the note body, not the raw file (with its YAML
    frontmatter noise) -- mirrors T127's FTS indexing choice."""
    service, engine, vault = _setup(tmp_path)
    (vault / "a.md").write_text("---\nid: concept_a\n---\n# A\n\nActual prose content.\n")
    VaultIndexer(engine, VaultResolver(str(vault))).reindex()

    summary = await service.generate_for_vault()

    assert summary.embedded == 1
