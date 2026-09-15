from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.base import Base


class VaultFileModel(Base):
    __tablename__ = "vault_files"
    __table_args__ = (Index("idx_vault_files_hash", "content_hash"),)

    path: Mapped[str] = mapped_column(primary_key=True)
    content_hash: Mapped[str]
    modified_at: Mapped[str]
    indexed_at: Mapped[str]
    file_type: Mapped[str]
