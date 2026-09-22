"""Deterministic, offline `EmbeddingProvider` for tests and Mock-provider
users (docs/TASKS.md T128, mirrors `mock.py`'s role for `AIProvider` --
see docs/AGENTS.md #17: mock is a real, legitimate offline choice).

Vectors are derived from each text's SHA-256 hash, not a real semantic
embedding -- meaningless for genuine similarity search, but stable
(same text always produces the same vector) and self-consistent (two
identical texts always compare as identical), which is everything a
deterministic test needs.
"""

import hashlib

DEFAULT_DIMS = 32


class MockEmbeddingProvider:
    def __init__(self, dims: int = DEFAULT_DIMS) -> None:
        self._dims = dims

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Repeat the 32-byte digest to cover any requested dimensionality,
        # then normalize each byte (0..255) into a small float in [-1, 1].
        raw = (digest * (self._dims // len(digest) + 1))[: self._dims]
        return [(byte / 127.5) - 1.0 for byte in raw]
