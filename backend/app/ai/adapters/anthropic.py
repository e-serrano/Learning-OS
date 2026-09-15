import json
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.ai.adapters._prompt import system_prompt, user_prompt
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.ai.protocol import AIRequest

_TOOL_NAME = "respond"


class AnthropicProvider:
    """Native Anthropic/Claude Messages API -- see docs/AI_CONTRACTS.md
    #17 and docs/AGENTS.md #20 (never treated as OpenAI-compatible).

    Structured output uses tool use: a single forced tool whose input
    schema is the requested response model, matching Anthropic's
    documented pattern for reliable structured output.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://api.anthropic.com/v1",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = client

    async def generate(self, request: AIRequest, response_model: type[BaseModel]) -> BaseModel:
        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 4096,
            "system": system_prompt(request),
            "messages": [{"role": "user", "content": user_prompt(request)}],
            "tools": [
                {
                    "name": _TOOL_NAME,
                    "description": "Provide the structured response.",
                    "input_schema": response_model.model_json_schema(),
                }
            ],
            "tool_choice": {"type": "tool", "name": _TOOL_NAME},
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        client = self._client or httpx.AsyncClient()
        owns_client = self._client is None
        try:
            response = await client.post(
                f"{self._base_url}/messages", json=payload, headers=headers, timeout=60.0
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AIProviderUnavailableError(str(exc)) from exc
        finally:
            if owns_client:
                await client.aclose()

        try:
            data = response.json()
            tool_block = next(
                block for block in data["content"] if block.get("type") == "tool_use"
            )
            return response_model.model_validate(tool_block["input"])
        except (KeyError, StopIteration, TypeError, json.JSONDecodeError, ValidationError) as exc:
            raise AIInvalidOutputError(str(exc)) from exc
