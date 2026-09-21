"""Live provider smoke matrix (docs/TASKS.md T122, docs/AGENTS.md #17:
"Live model tests belong in a separate optional suite").

Every adapter's happy path is already covered against `httpx.MockTransport`
(T051-T056, `tests/ai/adapters/test_provider_adapters.py`) -- no real
credentials, no network, runs in every CI job. What that suite cannot
prove is that a *real* provider actually accepts this codebase's request
shape and returns something the adapter can parse; that needs a live
round-trip, which needs real credentials this repo's CI never has
(docs/CONFIGURATION.md's env vars, T014, are the app's own runtime
config -- there is no committed test credential for any of these).

Each test below is skipped unless its own `LEARNINGOS_LIVE_*` env vars
are set, so the default `uv run pytest` (and CI's `backend` job) collects
these but always skips them -- "Mock in CI" from the task text. Run the
whole matrix locally with real credentials via, e.g.:

    LEARNINGOS_LIVE_OPENAI_API_KEY=sk-... LEARNINGOS_LIVE_OPENAI_MODEL=gpt-4o-mini \
        uv run pytest tests/live -v

No model id is hardcoded as a default -- a stale default would silently
start failing as providers deprecate models, and nothing here runs
without a human deliberately opting in and naming a model anyway.
"""

import os

import pytest
from pydantic import BaseModel

from app.ai.adapters.anthropic import AnthropicProvider
from app.ai.adapters.nvidia_nim import NvidiaNimProvider
from app.ai.adapters.ollama import OllamaProvider
from app.ai.adapters.openai import OpenAIProvider
from app.ai.adapters.openai_compatible import OpenAICompatibleProvider
from app.ai.adapters.openrouter import OpenRouterProvider
from app.ai.protocol import AIRequest


class SmokeResponse(BaseModel):
    answer: str


def _request() -> AIRequest:
    return AIRequest(
        role="smoke_test",
        prompt_version="smoke.v1",
        task={"instruction": "Reply with a short greeting in the `answer` field."},
    )


async def _assert_smoke(provider: object) -> None:
    response = await provider.generate(_request(), SmokeResponse)  # type: ignore[attr-defined]
    assert isinstance(response, SmokeResponse)
    assert response.answer.strip() != ""


@pytest.mark.skipif(
    not os.environ.get("LEARNINGOS_LIVE_OLLAMA_MODEL"),
    reason="set LEARNINGOS_LIVE_OLLAMA_MODEL (and optionally _BASE_URL) to run",
)
async def test_ollama_live_smoke() -> None:
    provider = OllamaProvider(
        model=os.environ["LEARNINGOS_LIVE_OLLAMA_MODEL"],
        base_url=os.environ.get("LEARNINGOS_LIVE_OLLAMA_BASE_URL", "http://localhost:11434"),
    )
    await _assert_smoke(provider)


@pytest.mark.skipif(
    not (
        os.environ.get("LEARNINGOS_LIVE_OPENAI_API_KEY")
        and os.environ.get("LEARNINGOS_LIVE_OPENAI_MODEL")
    ),
    reason="set LEARNINGOS_LIVE_OPENAI_API_KEY and LEARNINGOS_LIVE_OPENAI_MODEL to run",
)
async def test_openai_live_smoke() -> None:
    provider = OpenAIProvider(
        model=os.environ["LEARNINGOS_LIVE_OPENAI_MODEL"],
        api_key=os.environ["LEARNINGOS_LIVE_OPENAI_API_KEY"],
    )
    await _assert_smoke(provider)


@pytest.mark.skipif(
    not (
        os.environ.get("LEARNINGOS_LIVE_ANTHROPIC_API_KEY")
        and os.environ.get("LEARNINGOS_LIVE_ANTHROPIC_MODEL")
    ),
    reason="set LEARNINGOS_LIVE_ANTHROPIC_API_KEY and LEARNINGOS_LIVE_ANTHROPIC_MODEL to run",
)
async def test_anthropic_live_smoke() -> None:
    provider = AnthropicProvider(
        model=os.environ["LEARNINGOS_LIVE_ANTHROPIC_MODEL"],
        api_key=os.environ["LEARNINGOS_LIVE_ANTHROPIC_API_KEY"],
    )
    await _assert_smoke(provider)


@pytest.mark.skipif(
    not (
        os.environ.get("LEARNINGOS_LIVE_OPENROUTER_API_KEY")
        and os.environ.get("LEARNINGOS_LIVE_OPENROUTER_MODEL")
    ),
    reason="set LEARNINGOS_LIVE_OPENROUTER_API_KEY and LEARNINGOS_LIVE_OPENROUTER_MODEL to run",
)
async def test_openrouter_live_smoke() -> None:
    provider = OpenRouterProvider(
        model=os.environ["LEARNINGOS_LIVE_OPENROUTER_MODEL"],
        api_key=os.environ["LEARNINGOS_LIVE_OPENROUTER_API_KEY"],
    )
    await _assert_smoke(provider)


@pytest.mark.skipif(
    not (
        os.environ.get("LEARNINGOS_LIVE_NVIDIA_API_KEY")
        and os.environ.get("LEARNINGOS_LIVE_NVIDIA_MODEL")
        and os.environ.get("LEARNINGOS_LIVE_NVIDIA_BASE_URL")
    ),
    reason=(
        "set LEARNINGOS_LIVE_NVIDIA_API_KEY, LEARNINGOS_LIVE_NVIDIA_MODEL and "
        "LEARNINGOS_LIVE_NVIDIA_BASE_URL to run"
    ),
)
async def test_nvidia_nim_live_smoke() -> None:
    provider = NvidiaNimProvider(
        model=os.environ["LEARNINGOS_LIVE_NVIDIA_MODEL"],
        api_key=os.environ["LEARNINGOS_LIVE_NVIDIA_API_KEY"],
        base_url=os.environ["LEARNINGOS_LIVE_NVIDIA_BASE_URL"],
    )
    await _assert_smoke(provider)


@pytest.mark.skipif(
    not (
        os.environ.get("LEARNINGOS_LIVE_COMPATIBLE_BASE_URL")
        and os.environ.get("LEARNINGOS_LIVE_COMPATIBLE_MODEL")
    ),
    reason=(
        "set LEARNINGOS_LIVE_COMPATIBLE_BASE_URL and LEARNINGOS_LIVE_COMPATIBLE_MODEL "
        "(and optionally _API_KEY) to run"
    ),
)
async def test_openai_compatible_live_smoke() -> None:
    provider = OpenAICompatibleProvider(
        model=os.environ["LEARNINGOS_LIVE_COMPATIBLE_MODEL"],
        base_url=os.environ["LEARNINGOS_LIVE_COMPATIBLE_BASE_URL"],
        api_key=os.environ.get("LEARNINGOS_LIVE_COMPATIBLE_API_KEY"),
    )
    await _assert_smoke(provider)
