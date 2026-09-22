from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class VaultEmbeddingModel(Base):
    """One embedding vector per indexed vault file (docs/TASKS.md T128).

    `content_hash` mirrors the source `vault_files.content_hash` at the
    time this vector was generated -- `EmbeddingService` compares the two
    to skip re-embedding unchanged files, since a real provider's
    embeddings call costs money/quota, unlike `vault_files_fts`'s free
    local rebuild on every scan. `model` is stored alongside the vector
    because vectors from different embedding models live in different,
    mutually-incomparable spaces -- mixing them would silently corrupt
    any future similarity search (T129).
    """

    __tablename__ = "vault_embeddings"

    path: Mapped[str] = mapped_column(primary_key=True)
    content_hash: Mapped[str]
    model: Mapped[str]
    dims: Mapped[int]
    vector_json: Mapped[str]
    created_at: Mapped[str]
