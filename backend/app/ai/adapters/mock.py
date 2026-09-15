from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from app.ai.errors import AIInvalidOutputError
from app.ai.protocol import AIRequest

ModelT = TypeVar("ModelT", bound=BaseModel)
ResponseFactory = Callable[[AIRequest], BaseModel]


class MockProvider:
    """Deterministic, offline AIProvider for tests and onboarding fallback.

    Configure exact responses (or a failure) per response_model; no network
    calls are ever made. See docs/AGENTS.md #17.
    """

    def __init__(self) -> None:
        self._responses: dict[type[BaseModel], BaseModel | ResponseFactory] = {}
        self._error: Exception | None = None

    def set_response(
        self, response_model: type[ModelT], response: ModelT | Callable[[AIRequest], ModelT]
    ) -> None:
        self._responses[response_model] = response

    def set_error(self, error: Exception) -> None:
        self._error = error

    def clear_error(self) -> None:
        self._error = None

    async def generate(
        self,
        request: AIRequest,
        response_model: type[BaseModel],
    ) -> BaseModel:
        if self._error is not None:
            raise self._error

        configured = self._responses.get(response_model)
        if configured is None:
            raise AIInvalidOutputError(
                f"MockProvider has no configured response for {response_model.__name__}"
            )

        result = configured(request) if callable(configured) else configured
        if not isinstance(result, response_model):
            raise AIInvalidOutputError(
                f"MockProvider response for {response_model.__name__} "
                f"was configured with an incompatible type"
            )
        return result
