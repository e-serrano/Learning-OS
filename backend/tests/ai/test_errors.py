from app.ai.errors import AIInvalidOutputError


def test_str_stays_the_full_technical_detail() -> None:
    """RetryingProvider feeds `str(error)` back to the model as
    `previous_validation_error` on its one automatic retry
    (docs/AI_CONTRACTS.md #13) -- the specific field/type it got wrong is
    the whole point of that feedback, so this must never be watered
    down."""
    detail = "3 validation errors for ExerciseGeneratorResponse\ntype\n  ..."
    error = AIInvalidOutputError(detail)

    assert str(error) == detail


def test_user_message_defaults_to_a_generic_non_technical_summary() -> None:
    error = AIInvalidOutputError("KeyError('choices')")

    assert "choices" not in error.user_message
    assert "KeyError" not in error.user_message
    assert error.user_message  # non-empty


def test_user_message_can_be_overridden_with_something_more_specific() -> None:
    error = AIInvalidOutputError("detail", user_message="expected 3 embeddings, got 2")

    assert error.user_message == "expected 3 embeddings, got 2"
    assert str(error) == "detail"
