class AIProviderError(Exception):
    """Base class for AI provider failures. See docs/AI_CONTRACTS.md #13."""


class AIProviderUnavailableError(AIProviderError):
    """The provider could not be reached or rejected the request (auth, network)."""


_GENERIC_INVALID_OUTPUT_MESSAGE = (
    "The AI's response didn't match the expected format. This can happen with a "
    "less capable or overloaded model -- try again, or switch models in Settings."
)


class AIInvalidOutputError(AIProviderError):
    """The provider's response failed schema/business validation.

    `str(self)` (`args[0]`) stays the full technical detail -- a Pydantic
    `ValidationError` dump, a `KeyError`, whatever the adapter caught --
    because `RetryingProvider` feeds exactly that back to the model as
    `previous_validation_error` on its one automatic retry
    (docs/AI_CONTRACTS.md #13); the specific field/type it got wrong is
    the whole point of that feedback, an AI role a generic message can't
    serve. `user_message` is the separate, human-facing summary an API
    route should put in an HTTP response instead (docs/TASKS.md T153,
    reported live: the raw dump -- field names, internal type names, a
    pydantic.dev URL -- surfaced verbatim in the frontend's error
    message). Defaults to a generic explanation when the caller doesn't
    have anything more specific to say.
    """

    def __init__(self, detail: str, user_message: str | None = None) -> None:
        super().__init__(detail)
        self.user_message = user_message or _GENERIC_INVALID_OUTPUT_MESSAGE
