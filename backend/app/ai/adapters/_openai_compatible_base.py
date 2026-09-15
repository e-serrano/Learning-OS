import json
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.ai.adapters._prompt import system_prompt, user_prompt
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.ai.protocol import AIRequest


class OpenAICompatibleAdapter:
    """Shared Chat Completions wire client for genuinely OpenAI-compatible
    endpoints (OpenAI, OpenRouter, NVIDIA NIM, generic OpenAI-compatible).

    Anthropic and Ollama have their own native protocols and do NOT use
    this base -- see docs/AI_CONTRACTS.md #17 and docs/AGENTS.md #20
    (Anthropic is never treated as OpenAI-compatible).
    """

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

    async def generate(self, request: AIRequest, response_model: type[BaseModel]) -> BaseModel:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt(request)},
                {"role": "user", "content": user_prompt(request)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": response_model.model_json_schema(),
                    "strict": True,
                },
            },
        }

        client = self._client or httpx.AsyncClient()
        owns_client = self._client is None
        try:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AIProviderUnavailableError(str(exc)) from exc
        finally:
            if owns_client:
                await client.aclose()

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return response_model.model_validate(parsed)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            raise AIInvalidOutputError(str(exc)) from exc
