from typing import Any

import httpx

from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError


class OllamaEmbeddingProvider:
    """Local Ollama embeddings, native `/api/embed` (batched -- see
    docs/TASKS.md T128). Same "no credential, local default" shape as
    `ollama.py`'s chat adapter."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._client = client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        payload: dict[str, Any] = {"model": self._model, "input": texts}

        client = self._client or httpx.AsyncClient()
        owns_client = self._client is None
        try:
            response = await client.post(f"{self._base_url}/api/embed", json=payload, timeout=120.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AIProviderUnavailableError(str(exc)) from exc
        finally:
            if owns_client:
                await client.aclose()

        try:
            data = response.json()
            vectors = data["embeddings"]
        except (KeyError, TypeError, ValueError) as exc:
            raise AIInvalidOutputError(str(exc)) from exc

        if len(vectors) != len(texts):
            raise AIInvalidOutputError(
                f"expected {len(texts)} embeddings, provider returned {len(vectors)}"
            )
        try:
            return [[float(x) for x in vector] for vector in vectors]
        except (TypeError, ValueError) as exc:
            raise AIInvalidOutputError(str(exc)) from exc
