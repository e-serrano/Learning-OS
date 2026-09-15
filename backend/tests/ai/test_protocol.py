from app.ai.adapters.mock import MockProvider
from app.ai.protocol import AIProvider, AIRequest


def _accepts_provider(provider: AIProvider) -> AIProvider:
    """Type-checked by mypy: MockProvider must satisfy the AIProvider protocol."""
    return provider


def test_mock_provider_satisfies_ai_provider_protocol() -> None:
    provider = _accepts_provider(MockProvider())
    assert callable(provider.generate)


def test_ai_request_defaults_are_empty_containers() -> None:
    request = AIRequest(role="tutor", prompt_version="tutor.v1")
    assert request.goal == {}
    assert request.current_state == {}
    assert request.context == []
    assert request.task == {}
    assert request.constraints == {}
