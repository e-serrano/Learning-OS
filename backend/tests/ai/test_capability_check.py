import pytest

from app.ai.capability_check import check_provider_capability
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
