from typing import Any, Protocol

from pydantic import BaseModel, Field


class AIRequest(BaseModel):
    """Common request envelope -- see docs/AI_CONTRACTS.md #2.

    Never carries credential values (docs/AI_CONTRACTS.md #18); adapters
    resolve secrets themselves from CredentialStore at call time.
    """

    role: str
    prompt_version: str
    goal: dict[str, Any] = Field(default_factory=dict)
    current_state: dict[str, Any] = Field(default_factory=dict)
    context: list[Any] = Field(default_factory=list)
    task: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)


class AIProvider(Protocol):
    """Every provider adapter implements this -- see docs/AI_CONTRACTS.md #3.

    The learning engine depends only on this protocol, never on a specific
    provider's implementation details (docs/AGENTS.md #20).
    """

    async def generate(
        self,
        request: AIRequest,
        response_model: type[BaseModel],
    ) -> BaseModel: ...
