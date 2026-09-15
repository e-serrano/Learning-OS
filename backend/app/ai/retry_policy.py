from pydantic import BaseModel

from app.ai.errors import AIInvalidOutputError, AIProviderError
from app.ai.protocol import AIProvider, AIRequest


def _with_validation_error(request: AIRequest, error_message: str) -> AIRequest:
    """A fresh request carrying the previous attempt's validation error, so
    the model can self-correct on retry."""
    constraints = {**request.constraints, "previous_validation_error": error_message}
    return request.model_copy(update={"constraints": constraints})


class RetryingProvider:
    """Wraps an AIProvider with docs/AI_CONTRACTS.md #13's failure policy:

        validate -> retry once with the validation error -> fallback -> surface failure

    Invalid output never mutates application state (docs/AGENTS.md #5):
    if every attempt fails, the original exception propagates instead of
    silently returning something unvalidated.
    """

    def __init__(self, primary: AIProvider, fallback: AIProvider | None = None) -> None:
        self._primary = primary
        self._fallback = fallback

    async def generate(self, request: AIRequest, response_model: type[BaseModel]) -> BaseModel:
        try:
            return await self._primary.generate(request, response_model)
        except AIInvalidOutputError as first_error:
            try:
                retry_request = _with_validation_error(request, str(first_error))
                return await self._primary.generate(retry_request, response_model)
            except AIInvalidOutputError as second_error:
                return await self._fall_back(request, response_model, second_error)
        except AIProviderError as unavailable_error:
            return await self._fall_back(request, response_model, unavailable_error)

    async def _fall_back(
        self,
        request: AIRequest,
        response_model: type[BaseModel],
        original_error: AIProviderError,
    ) -> BaseModel:
        if self._fallback is None:
            raise original_error
        try:
            return await self._fallback.generate(request, response_model)
        except AIProviderError:
            raise original_error from None
