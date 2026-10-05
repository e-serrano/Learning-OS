import json
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.ai.adapters._http_errors import provider_unavailable_error
from app.ai.adapters._prompt import system_prompt, user_prompt
from app.ai.errors import AIInvalidOutputError
from app.ai.protocol import AIRequest


async def list_ollama_models(base_url: str, client: httpx.AsyncClient | None = None) -> list[str]:
    """Names of the models the user has pulled locally (`GET /api/tags`),
    so Settings can offer them in a dropdown instead of a free-text field
    (docs/TASKS.md T163, user request)."""
    owns_client = client is None
    client = client or httpx.AsyncClient()
    try:
        response = await client.get(f"{base_url.rstrip('/')}/api/tags", timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise provider_unavailable_error(exc) from exc
    finally:
        if owns_client:
            await client.aclose()

    try:
        return sorted(model["name"] for model in response.json()["models"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AIInvalidOutputError(str(exc)) from exc


class OllamaProvider:
    """Local Ollama endpoint, native /api/chat -- see docs/AI_CONTRACTS.md
    #17. Uses Ollama's own structured-output support (the `format` field
    set to a JSON schema) rather than its OpenAI-compatibility shim, since
    no credential is required and the native API is more directly
    documented for this."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._client = client

    async def generate(self, request: AIRequest, response_model: type[BaseModel]) -> BaseModel:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt(request)},
                {"role": "user", "content": user_prompt(request)},
            ],
            "format": response_model.model_json_schema(),
            "stream": False,
        }

        client = self._client or httpx.AsyncClient()
        owns_client = self._client is None
        try:
            response = await client.post(f"{self._base_url}/api/chat", json=payload, timeout=120.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise provider_unavailable_error(exc) from exc
        finally:
            if owns_client:
                await client.aclose()

        try:
            data = response.json()
            content = data["message"]["content"]
            parsed = json.loads(content)
            return response_model.model_validate(parsed)
        except (KeyError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            raise AIInvalidOutputError(str(exc)) from exc
