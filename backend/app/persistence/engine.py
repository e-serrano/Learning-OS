from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event


def create_sqlite_engine(db_path: str) -> Engine:
    """Create a SQLite engine with the settings docs/AGENTS.md #8 requires.

    Foreign keys enabled, WAL journal mode, a busy timeout so concurrent
    local readers/writers don't immediately error, and the parent directory
    created if missing (SQLite never creates directories itself).
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite:///{db_path}")

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

    return engine
