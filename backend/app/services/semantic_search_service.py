"""Semantic (embedding-similarity) search over vault content (docs/TASKS.md
T129 -- the retrieval half of the embeddings infrastructure T128 built).

Deliberately a separate route/service from `vault_search_service.py`'s
lexical FTS search, not a merged "smart search": the two have different
failure modes (a malformed FTS query vs. an unreachable/unconfigured
embedding provider) and different costs (free/local vs. a real network
call per query), so collapsing them would hide which one actually
failed and make every text search pay an AI-provider round trip.

Only compares against `vault_embeddings` rows whose `model` matches the
orchestrator's current model -- vectors from a different embedding
model live in a different, incomparable space (same reasoning as
`vault_embedding.py`'s own docstring), so a provider/model change
between generate calls must never silently mix stale vectors into a
similarity ranking instead of just being excluded from it.

No numpy dependency (not already a dependency of this backend, and
vault-scale note counts don't need vectorized performance) -- cosine
similarity is computed in plain Python.
"""

import json
import math
from dataclasses import dataclass

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session as DbSession

from app.ai.embedding_orchestrator import EmbeddingOrchestrator
from app.persistence.models import VAULT_SEARCH_FTS_TABLE, VaultEmbeddingModel
from app.services.vault_search_service import InvalidSearchQueryError

__all__ = ["InvalidSearchQueryError", "SemanticSearchResult", "SemanticSearchService"]

DEFAULT_LIMIT = 10


@dataclass(frozen=True)
class SemanticSearchResult:
    path: str
    title: str
    score: float


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticSearchService:
    def __init__(self, engine: Engine, orchestrator: EmbeddingOrchestrator) -> None:
        self._engine = engine
        self._orchestrator = orchestrator

    async def search(self, query: str, limit: int = DEFAULT_LIMIT) -> list[SemanticSearchResult]:
        stripped = query.strip()
        if not stripped:
            raise InvalidSearchQueryError("query must not be blank")

        with DbSession(self._engine) as db:
            candidates = list(
                db.scalars(
                    select(VaultEmbeddingModel).where(
                        VaultEmbeddingModel.model == self._orchestrator.model
                    )
                )
            )

        if not candidates:
            return []

        query_vector = (await self._orchestrator.embed([stripped]))[0]

        # Same `model` name is the usual dims guarantee, but not an
        # absolute one (e.g. a provider reconfigured with a different
        # dimensionality under the same model string) -- a mismatched
        # row is skipped, not a reason to fail the whole search.
        scored = [
            (row.path, _cosine_similarity(query_vector, vector))
            for row in candidates
            if len(vector := json.loads(row.vector_json)) == len(query_vector)
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        top = scored[:limit]

        titles = self._titles_for([path for path, _ in top])
        return [
            SemanticSearchResult(path=path, title=titles.get(path, path), score=score)
            for path, score in top
        ]

    def _titles_for(self, paths: list[str]) -> dict[str, str]:
        if not paths:
            return {}
        with self._engine.connect() as conn:
            placeholders = ", ".join(f":p{i}" for i in range(len(paths)))
            params = {f"p{i}": path for i, path in enumerate(paths)}
            rows = conn.execute(
                text(
                    f"SELECT path, title FROM {VAULT_SEARCH_FTS_TABLE} "  # noqa: S608
                    f"WHERE path IN ({placeholders})"
                ),
                params,
            )
            return {row.path: row.title for row in rows}
