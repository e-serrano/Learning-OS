"""Single entry point for all embedding provider calls (docs/TASKS.md
T128) -- the embeddings sibling of `orchestrator.py`. Kept separate
rather than folded into `AIOrchestrator` because embeddings have no
`AIRequest`/`response_model` to log against; this logs the same
`ai_runs` audit trail (docs/AGENTS.md #21) with a fixed `role` and
`prompt_version` instead, hashing the joined input texts.
"""

import hashlib
import time
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.ai.embedding_protocol import EmbeddingProvider
from app.persistence.models import AIRunModel

EMBEDDING_ROLE = "embedding"
EMBEDDING_PROMPT_VERSION = "embedding.v1"


def _input_hash(texts: list[str]) -> str:
    return hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()


class EmbeddingOrchestrator:
    def __init__(
        self, engine: Engine, provider: EmbeddingProvider, provider_name: str, model: str
    ) -> None:
        self._engine = engine
        self._provider = provider
        self._provider_name = provider_name
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        started = time.monotonic()
        success = False
        error_type: str | None = None
        try:
            result = await self._provider.embed(texts)
            success = True
            return result
        except Exception as exc:
            error_type = type(exc).__name__
            raise
        finally:
            latency_ms = int((time.monotonic() - started) * 1000)
            self._log_run(texts, latency_ms, success, error_type)

    def _log_run(
        self, texts: list[str], latency_ms: int, success: bool, error_type: str | None
    ) -> None:
        with DbSession(self._engine) as db:
            db.add(
                AIRunModel(
                    id=f"ai_run_{uuid4().hex}",
                    session_id=None,
                    role=EMBEDDING_ROLE,
                    provider=self._provider_name,
                    model=self._model,
                    prompt_version=EMBEDDING_PROMPT_VERSION,
                    input_hash=_input_hash(texts),
                    output_schema="Embedding",
                    latency_ms=latency_ms,
                    success=success,
                    error_type=error_type,
                    created_at=datetime.now(UTC).isoformat(),
                )
            )
            db.commit()
