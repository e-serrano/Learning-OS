"""Shared `POST {base_url}/embeddings` wire client (docs/TASKS.md T128),
the embeddings-endpoint sibling of `_openai_compatible_base.py`'s Chat
Completions client -- same genuinely-OpenAI-compatible provider set
(OpenAI, OpenRouter, NVIDIA NIM, generic OpenAI-compatible), different
endpoint and request/response shape entirely.

Anthropic has no embeddings endpoint at all (docs/AI_CONTRACTS.md #17
precedent: never treated as OpenAI-compatible) and Ollama uses its own
native `/api/embed` protocol (`ollama_embeddings.py`), so neither uses
this base.
"""

import httpx

from app.ai.adapters._http_errors import provider_unavailable_error
from app.ai.errors import AIInvalidOutputError


class OpenAICompatibleEmbeddingAdapter:
    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {"model": self._model, "input": texts}

        client = self._client or httpx.AsyncClient()
        owns_client = self._client is None
        try:
            response = await client.post(
                f"{self._base_url}/embeddings", json=payload, headers=headers, timeout=60.0
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise provider_unavailable_error(exc) from exc
        finally:
            if owns_client:
                await client.aclose()

        try:
            data = response.json()
            by_index = sorted(data["data"], key=lambda item: item["index"])
            vectors = [item["embedding"] for item in by_index]
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
