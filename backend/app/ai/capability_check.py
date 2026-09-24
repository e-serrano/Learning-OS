from pydantic import BaseModel

from app.ai.adapters.anthropic import AnthropicProvider
from app.ai.adapters.nvidia_nim import NvidiaNimProvider
from app.ai.adapters.ollama import OllamaProvider
from app.ai.adapters.openai import OpenAIProvider
from app.ai.adapters.openai_compatible import OpenAICompatibleProvider
from app.ai.adapters.openrouter import OpenRouterProvider
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.ai.protocol import AIProvider, AIRequest
from app.ai.provider_registry import ProviderId, get_provider_descriptor

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
"""Mirrors `app/ai/provider_factory.py`'s own constant -- not imported
from there, see `_build_probe_adapter`'s docstring for why."""


class CapabilityCheckResult(BaseModel):
    """Result of validating a provider configuration -- see docs/AI_CONTRACTS.md #19.

    Never carries credential values (docs/AI_CONTRACTS.md #20).
    """

    ok: bool
    provider_id: ProviderId
    reason: str | None = None


def check_provider_capability(
    provider_id: ProviderId,
    model: str | None,
    base_url: str | None,
    credential: str | None,
) -> CapabilityCheckResult:
    """Structural pre-check: required credential/base_url/model are present.

    Takes primitives rather than AIProviderConfig so app.ai never depends on
    app.config (app.config already depends on app.ai for ProviderId).

    This never sends vault content, and never touches the network -- it only
    validates the configuration against the provider's declared requirements
    (docs/AI_CONTRACTS.md #16). Callers should run this first and only call
    `validate_provider_connection` (below) if it returns `ok=True` -- there
    is no point making a real network call for a config that's already known
    to be incomplete, and this function's checks are the ones that catch
    "no credential typed at all" without wasting a request.
    """
    descriptor = get_provider_descriptor(provider_id)

    if descriptor.requires_api_key and not credential:
        return CapabilityCheckResult(
            ok=False,
            provider_id=provider_id,
            reason="Missing required API credential",
        )
    if descriptor.requires_base_url and not base_url:
        return CapabilityCheckResult(
            ok=False,
            provider_id=provider_id,
            reason="Missing required base_url",
        )
    if not model:
        return CapabilityCheckResult(
            ok=False,
            provider_id=provider_id,
            reason="Missing model",
        )
    if not descriptor.supports_structured_output:
        return CapabilityCheckResult(
            ok=False,
            provider_id=provider_id,
            reason="Provider does not declare structured-output support",
        )

    return CapabilityCheckResult(ok=True, provider_id=provider_id)


class _CapabilityProbeResponse(BaseModel):
    answer: str


def _probe_request() -> AIRequest:
    """Unregistered `prompt_version` (not in `PROMPT_REGISTRY`) is fine --
    `_prompt.py`'s `system_prompt()` degrades to a generic role-based
    instruction for an unknown version rather than failing, same as
    `backend/tests/live/test_provider_smoke.py`'s own probe request."""
    return AIRequest(
        role="capability_check",
        prompt_version="capability_check.v1",
        task={"instruction": "Reply with a short greeting in the `answer` field."},
    )


def _build_probe_adapter(
    provider_id: ProviderId, model: str, base_url: str | None, credential: str | None
) -> AIProvider:
    """Mirrors `app/ai/provider_factory.py`'s `_build_adapter` per-provider
    switch, but takes primitives instead of `AIProviderConfig`. Deliberately
    NOT imported from there: `provider_factory.py` imports `app.config`
    (`AIProviderConfig`, `CredentialStore`), and this module's own
    `check_provider_capability` docstring already commits to keeping
    `app.ai` independent of `app.config` (which itself depends on `app.ai`
    for `ProviderId`) -- reusing that factory here would run the
    dependency backward, so the small per-provider switch is duplicated
    instead. Only ever called after `check_provider_capability` returned
    `ok=True`, so required fields are already known present -- no
    defensive re-validation here."""
    if provider_id == ProviderId.OLLAMA:
        return OllamaProvider(model=model, base_url=base_url or DEFAULT_OLLAMA_BASE_URL)
    if provider_id == ProviderId.OPENAI:
        assert credential is not None
        return OpenAIProvider(model=model, api_key=credential)
    if provider_id == ProviderId.ANTHROPIC:
        assert credential is not None
        return AnthropicProvider(model=model, api_key=credential)
    if provider_id == ProviderId.OPENROUTER:
        assert credential is not None
        assert base_url is not None
        return OpenRouterProvider(model=model, api_key=credential, base_url=base_url)
    if provider_id == ProviderId.NVIDIA_NIM:
        assert credential is not None
        assert base_url is not None
        return NvidiaNimProvider(model=model, api_key=credential, base_url=base_url)
    if provider_id == ProviderId.OPENAI_COMPATIBLE:
        assert base_url is not None
        return OpenAICompatibleProvider(model=model, base_url=base_url, api_key=credential)
    raise ValueError(f"unknown provider id for a live probe: {provider_id!r}")


async def validate_provider_connection(
    provider_id: ProviderId,
    model: str,
    base_url: str | None,
    credential: str | None,
) -> CapabilityCheckResult:
    """Live counterpart to `check_provider_capability` (docs/TASKS.md T145,
    docs/AI_CONTRACTS.md #19: "validate connection, credential ... model
    and minimum structured-output capability"). Makes exactly one minimal
    real request -- the same trivial one-field schema/prompt shape
    `test_provider_smoke.py` already uses for its own live checks -- and
    reports whether the provider actually accepted it, rather than only
    whether the configuration was well-formed.

    `mock` is exempt: it is deterministic and offline by design (see
    `app/ai/adapters/mock.py`), "reachable" isn't a meaningful question
    for it, and it has no canned response configured for this probe's
    schema outside test code -- calling it here would always fail one of
    the app's explicitly zero-setup paths (docs/DEVELOPMENT.md: "the
    bundled Mock provider ... is enough to explore the app").

    Never wrapped in `RetryingProvider`/fallback -- the entire point of a
    connection test is whether the *first* real attempt succeeds.
    """
    if provider_id == ProviderId.MOCK:
        return CapabilityCheckResult(ok=True, provider_id=provider_id)

    try:
        adapter = _build_probe_adapter(provider_id, model, base_url, credential)
        await adapter.generate(_probe_request(), _CapabilityProbeResponse)
    except (AIProviderUnavailableError, AIInvalidOutputError) as exc:
        return CapabilityCheckResult(ok=False, provider_id=provider_id, reason=str(exc))

    return CapabilityCheckResult(ok=True, provider_id=provider_id)
