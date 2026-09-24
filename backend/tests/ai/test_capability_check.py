import pytest
from pydantic import BaseModel

from app.ai import capability_check
from app.ai.adapters.anthropic import AnthropicProvider
from app.ai.adapters.ollama import OllamaProvider
from app.ai.capability_check import (
    _build_probe_adapter,
    check_provider_capability,
    validate_provider_connection,
)
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.ai.protocol import AIRequest
from app.ai.provider_registry import ProviderId


def test_mock_provider_always_ok_no_credential_no_base_url() -> None:
    result = check_provider_capability(
        provider_id=ProviderId.MOCK, model="mock-1", base_url=None, credential=None
    )
    assert result.ok is True
    assert result.reason is None


def test_remote_provider_missing_credential_fails() -> None:
    result = check_provider_capability(
        provider_id=ProviderId.OPENAI, model="gpt-5", base_url=None, credential=None
    )
    assert result.ok is False
    assert result.reason == "Missing required API credential"


def test_remote_provider_with_credential_passes() -> None:
    result = check_provider_capability(
        provider_id=ProviderId.OPENAI, model="gpt-5", base_url=None, credential="sk-abc"
    )
    assert result.ok is True


def test_provider_requiring_base_url_without_one_fails() -> None:
    result = check_provider_capability(
        provider_id=ProviderId.OLLAMA, model="llama3", base_url=None, credential=None
    )
    assert result.ok is False
    assert result.reason == "Missing required base_url"


def test_provider_with_base_url_passes() -> None:
    result = check_provider_capability(
        provider_id=ProviderId.OLLAMA,
        model="llama3",
        base_url="http://localhost:11434",
        credential=None,
    )
    assert result.ok is True


def test_missing_model_fails_even_with_credential_and_base_url() -> None:
    result = check_provider_capability(
        provider_id=ProviderId.OPENAI, model=None, base_url=None, credential="sk-abc"
    )
    assert result.ok is False
    assert result.reason == "Missing model"


def test_openai_compatible_lacks_declared_structured_output_support() -> None:
    result = check_provider_capability(
        provider_id=ProviderId.OPENAI_COMPATIBLE,
        model="local-model",
        base_url="http://localhost:8080/v1",
        credential=None,
    )
    assert result.ok is False
    assert result.reason == "Provider does not declare structured-output support"


def test_result_never_carries_the_credential_value() -> None:
    result = check_provider_capability(
        provider_id=ProviderId.ANTHROPIC,
        model="claude-x",
        base_url=None,
        credential="sk-super-secret",
    )
    assert "sk-super-secret" not in result.model_dump_json()


@pytest.mark.parametrize(
    "provider_id", [ProviderId.OPENAI, ProviderId.ANTHROPIC, ProviderId.OPENROUTER]
)
def test_result_provider_id_matches_input(provider_id: ProviderId) -> None:
    result = check_provider_capability(
        provider_id=provider_id, model="m", base_url="http://x", credential="k"
    )
    assert result.provider_id == provider_id


# --- validate_provider_connection (docs/TASKS.md T145) ---------------------
#
# `_build_probe_adapter` is monkeypatched rather than injecting a real
# `httpx.MockTransport` per provider: each adapter's own wire protocol is
# already thoroughly covered in `tests/ai/adapters/` (headers, body shape,
# error parsing). What's specific to `validate_provider_connection` is its
# own logic -- mock's exemption, success/failure mapping, never retrying --
# independent of which concrete adapter answered.


class _FakeAdapter:
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    async def generate(self, request: AIRequest, response_model: type[BaseModel]) -> BaseModel:
        if self._error is not None:
            raise self._error
        return response_model(answer="hi")  # type: ignore[call-arg]


@pytest.mark.asyncio
async def test_mock_is_always_ok_without_ever_building_an_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _must_not_be_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("mock must never reach _build_probe_adapter")

    monkeypatch.setattr(capability_check, "_build_probe_adapter", _must_not_be_called)

    result = await validate_provider_connection(
        provider_id=ProviderId.MOCK, model="mock-1", base_url=None, credential=None
    )

    assert result.ok is True


@pytest.mark.asyncio
async def test_succeeds_when_the_adapter_answers() -> None:
    def _fake_adapter(*args: object, **kwargs: object) -> _FakeAdapter:
        return _FakeAdapter()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(capability_check, "_build_probe_adapter", _fake_adapter)
        result = await validate_provider_connection(
            provider_id=ProviderId.OPENAI, model="gpt-5", base_url=None, credential="sk-abc"
        )

    assert result.ok is True
    assert result.reason is None


@pytest.mark.asyncio
async def test_reports_the_providers_own_error_reason() -> None:
    error = AIProviderUnavailableError("model: bad-id is not a valid model ID")

    def _fake_adapter(*args: object, **kwargs: object) -> _FakeAdapter:
        return _FakeAdapter(error=error)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(capability_check, "_build_probe_adapter", _fake_adapter)
        result = await validate_provider_connection(
            provider_id=ProviderId.ANTHROPIC, model="bad-id", base_url=None, credential="sk-ant"
        )

    assert result.ok is False
    assert result.reason == "model: bad-id is not a valid model ID"


@pytest.mark.asyncio
async def test_catches_invalid_output_too_not_only_unavailable() -> None:
    error = AIInvalidOutputError("response missing the answer field")

    def _fake_adapter(*args: object, **kwargs: object) -> _FakeAdapter:
        return _FakeAdapter(error=error)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(capability_check, "_build_probe_adapter", _fake_adapter)
        result = await validate_provider_connection(
            provider_id=ProviderId.OLLAMA,
            model="llama3",
            base_url="http://localhost:11434",
            credential=None,
        )

    assert result.ok is False
    assert result.reason == "response missing the answer field"


def test_build_probe_adapter_wires_anthropic_with_the_given_model_and_key() -> None:
    adapter = _build_probe_adapter(ProviderId.ANTHROPIC, "claude-x", None, "sk-ant")

    assert isinstance(adapter, AnthropicProvider)


def test_build_probe_adapter_falls_back_to_the_default_ollama_base_url() -> None:
    adapter = _build_probe_adapter(ProviderId.OLLAMA, "llama3", None, None)

    assert isinstance(adapter, OllamaProvider)
