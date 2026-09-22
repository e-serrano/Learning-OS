"""Generates and persists embedding vectors for indexed vault content
(docs/TASKS.md T128).

Deliberately a separate, explicit action (`POST /vault/embeddings/generate`),
not wired into `VaultIndexer.reindex()` the way `vault_files_fts` (T127)
is. FTS rebuilding is a free local computation piggybacked onto a scan
that already reads every file; a real embedding provider's call costs
money/quota per file, so it must never fire silently as a side effect of
an action (`/vault/scan`) the user didn't know would spend it.

Only re-embeds a file when its `vault_files.content_hash` no longer
matches the hash stored alongside its last embedding -- unchanged files
are skipped, so repeated runs stay cheap.
"""

import json
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.ai.embedding_orchestrator import EmbeddingOrchestrator
from app.obsidian.frontmatter import parse_frontmatter
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.models import VaultEmbeddingModel, VaultFileModel


class EmbeddingGenerationSummary(BaseModel):
    files_total: int
    embedded: int
    skipped_unchanged: int
    model: str


class EmbeddingService:
    def __init__(
        self, engine: Engine, resolver: VaultResolver, orchestrator: EmbeddingOrchestrator
    ) -> None:
        self._engine = engine
        self._resolver = resolver
        self._orchestrator = orchestrator

    async def generate_for_vault(self) -> EmbeddingGenerationSummary:
        with DbSession(self._engine) as db:
            files = [row for row in db.scalars(select(VaultFileModel)) if not row.missing]
            existing_hashes = {
                row.path: row.content_hash for row in db.scalars(select(VaultEmbeddingModel))
            }

        to_embed = [f for f in files if existing_hashes.get(f.path) != f.content_hash]
        skipped = len(files) - len(to_embed)

        if not to_embed:
            return EmbeddingGenerationSummary(
                files_total=len(files),
                embedded=0,
                skipped_unchanged=skipped,
                model=self._orchestrator.model,
            )

        texts = [self._read_body(f.path) for f in to_embed]
        vectors = await self._orchestrator.embed(texts)

        now = datetime.now(UTC).isoformat()
        with DbSession(self._engine) as db:
            for file_row, vector in zip(to_embed, vectors, strict=True):
                row = db.get(VaultEmbeddingModel, file_row.path)
                if row is None:
                    row = VaultEmbeddingModel(path=file_row.path)
                    db.add(row)
                row.content_hash = file_row.content_hash
                row.model = self._orchestrator.model
                row.dims = len(vector)
                row.vector_json = json.dumps(vector)
                row.created_at = now
            db.commit()

        return EmbeddingGenerationSummary(
            files_total=len(files),
            embedded=len(to_embed),
            skipped_unchanged=skipped,
            model=self._orchestrator.model,
        )

    def _read_body(self, path: str) -> str:
        content = self._resolver.resolve(path).read_text(encoding="utf-8")
        return parse_frontmatter(content).body
