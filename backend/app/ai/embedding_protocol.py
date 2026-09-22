"""Embedding provider protocol (docs/TASKS.md T128).

Deliberately separate from `AIProvider`/`app/ai/protocol.py`: that
protocol's single `generate(request, response_model) -> BaseModel`
method is shaped for structured chat-completion output matching one of
AI_CONTRACTS.md's 7 roles -- an embeddings endpoint returns raw vectors
for arbitrary text, a different wire protocol entirely (Anthropic has no
embeddings endpoint at all; the ones that exist don't share a request/
response shape with chat completions). Forcing embeddings through
`AIProvider.generate()` would mean inventing a fake `AIRequest`/
`response_model` pair with no real meaning.

Batched from the start (`texts: list[str]`) since every real caller
(`EmbeddingService`, T128) embeds many vault notes per run, not one at a
time.
"""

from typing import Protocol


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Returns one embedding vector per input text, same order,
        same length as `texts`."""
        ...
