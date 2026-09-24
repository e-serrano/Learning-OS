import httpx
import pytest

from app.ai.adapters._http_errors import provider_unavailable_error
from app.ai.errors import AIProviderUnavailableError


def _status_error(status_code: int, body: str) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://example.test/v1/messages")
    response = httpx.Response(status_code, text=body, request=request)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return exc
    raise AssertionError("expected raise_for_status to raise")


def test_status_error_includes_the_response_body() -> None:
    body = (
        '{"type":"error","error":{"type":"invalid_request_error",'
        '"message":"model: bad-model-id is not a valid model ID"}}'
    )
    exc = _status_error(400, body)

    result = provider_unavailable_error(exc)

    assert isinstance(result, AIProviderUnavailableError)
    assert "bad-model-id is not a valid model ID" in str(result)
    assert "400" in str(result)


def test_connection_level_error_falls_back_to_the_plain_message() -> None:
    """A `ConnectError`/`TimeoutException` never reached a server, so there
    is no response body to read -- must not crash trying to read one."""
    request = httpx.Request("POST", "https://example.test/v1/messages")
    exc = httpx.ConnectError("connection refused", request=request)

    result = provider_unavailable_error(exc)

    assert isinstance(result, AIProviderUnavailableError)
    assert "connection refused" in str(result)


@pytest.mark.parametrize("status_code", [401, 403, 404, 429, 500, 503])
def test_status_error_body_is_included_for_a_range_of_status_codes(status_code: int) -> None:
    exc = _status_error(status_code, "distinctive-body-marker")

    result = provider_unavailable_error(exc)

    assert "distinctive-body-marker" in str(result)
