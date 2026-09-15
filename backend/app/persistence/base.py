from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for SQLAlchemy models (docs/DATABASE_SCHEMA.md).

    Tables are added in T033. This exists now so Alembic's env.py has a
    stable target_metadata to point at.
    """
