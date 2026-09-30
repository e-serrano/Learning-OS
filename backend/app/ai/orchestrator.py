import asyncio
import hashlib
import time
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.ai.errors import AIProviderUnavailableError
from app.ai.protocol import AIProvider, AIRequest
from app.persistence.models import AIRunModel

# Comfortably under nginx's proxy_read_timeout (180s, docs/TASKS.md T152)
# -- a real project-generation call was observed taking 419s (primary +
# retry + fallback, each adapter-level timeout=60s not actually bounding
# wall-clock time when a provider trickles keep-alive bytes), so nginx
# killed the connection and the user saw a raw, unhandled 504 instead of
# a clean error (docs/TASKS.md T161). This is the one place every AI
# call already funnels through, so it's the one place a hard deadline
# guarantees the backend always answers before nginx does.
DEFAULT_PROVIDER_TIMEOUT_SECONDS = 150.0


def _input_hash(request: AIRequest) -> str:
    return hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()


class AIOrchestrator:
    """Single entry point for all provider calls -- see docs/AI_CONTRACTS.md
    and docs/DATABASE_SCHEMA.md (ai_runs).

    Every call is logged to ai_runs, success or failure, with latency and
    an input hash -- never the raw prompt/response (docs/AI_CONTRACTS.md
    #14). Callers depend only on AIProvider (docs/AGENTS.md #20); this
    class never branches on which concrete provider it holds.
    """

    def __init__(
        self,
        engine: Engine,
        provider: AIProvider,
        provider_name: str,
        model: str,
        language: str = "en",
        timeout_seconds: float = DEFAULT_PROVIDER_TIMEOUT_SECONDS,
    ) -> None:
        self._engine = engine
        self._provider = provider
        self._provider_name = provider_name
        self._model = model
        self._language = language
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        """Exposed so callers can stamp the same provenance (provider,
        model) they already log to ai_runs onto their own evidentiary
        records -- e.g. Evaluation.provider (docs/TASKS.md T073)."""
        return self._provider_name

    @property
    def model(self) -> str:
        return self._model

    async def generate(
        self,
        request: AIRequest,
        response_model: type[BaseModel],
        session_id: str | None = None,
    ) -> BaseModel:
        if "language" not in request.constraints:
            request = request.model_copy(
                update={"constraints": {**request.constraints, "language": self._language}}
            )
        started = time.monotonic()
        success = False
        error_type: str | None = None
        try:
            result = await asyncio.wait_for(
                self._provider.generate(request, response_model), timeout=self._timeout_seconds
            )
            success = True
            return result
        except TimeoutError as exc:
            error_type = "AIProviderUnavailableError"
            raise AIProviderUnavailableError(
                f"The AI provider did not respond within {int(self._timeout_seconds)}s."
            ) from exc
        except Exception as exc:
            error_type = type(exc).__name__
            raise
        finally:
            latency_ms = int((time.monotonic() - started) * 1000)
            self._log_run(request, response_model, session_id, latency_ms, success, error_type)

    def _log_run(
        self,
        request: AIRequest,
        response_model: type[BaseModel],
        session_id: str | None,
        latency_ms: int,
        success: bool,
        error_type: str | None,
    ) -> None:
        with DbSession(self._engine) as db:
            db.add(
                AIRunModel(
                    id=f"ai_run_{uuid4().hex}",
                    session_id=session_id,
                    role=request.role,
                    provider=self._provider_name,
                    model=self._model,
                    prompt_version=request.prompt_version,
                    input_hash=_input_hash(request),
                    output_schema=response_model.__name__,
                    latency_ms=latency_ms,
                    success=success,
                    error_type=error_type,
                    created_at=datetime.now(UTC).isoformat(),
                )
            )
            db.commit()
