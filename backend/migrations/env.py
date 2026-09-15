from logging.config import fileConfig

from alembic import context

from app.config.settings import Settings
from app.persistence import models  # noqa: F401  (registers ORM tables on Base.metadata)
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Resolve the DB path the same way the running app does (LEARNINGOS_DB_PATH
# env var, falling back to Settings' default) rather than a static URL in
# alembic.ini, so `alembic upgrade head` always targets the real app DB.
db_path = Settings().db_path


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL, no DB connection)."""
    context.configure(
        url=f"sqlite:///{db_path}",
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode, against the real app DB."""
    connectable = create_sqlite_engine(db_path)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
