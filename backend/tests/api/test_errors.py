from app.api.errors import NORMATIVE_ERROR_CODES, api_error


def test_api_error_builds_the_documented_envelope() -> None:
    exc = api_error("NOT_FOUND", "Goal 'x' not found", 404)

    assert exc.status_code == 404
    assert exc.detail == {
        "error": {"code": "NOT_FOUND", "message": "Goal 'x' not found", "details": {}}
    }


def test_normative_error_codes_matches_api_spec() -> None:
    assert NORMATIVE_ERROR_CODES == {
        "VALIDATION_ERROR",
        "NOT_FOUND",
        "CONFLICT",
        "VAULT_UNAVAILABLE",
        "VAULT_CONFLICT",
        "AI_UNAVAILABLE",
        "AI_INVALID_OUTPUT",
        "SESSION_STATE_ERROR",
        "PERMISSION_DENIED",
    }
