from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _config() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("LEARNINGOS_DB_PATH", str(path))
    return path


def test_upgrade_head_runs_against_empty_database_and_creates_version_table(
    db_path: Path,
) -> None:
    command.upgrade(_config(), "head")

    assert db_path.exists()
    engine = create_engine(f"sqlite:///{db_path}")
    assert "alembic_version" in inspect(engine).get_table_names()


def test_current_revision_matches_script_head_after_upgrade(db_path: Path) -> None:
    cfg = _config()
    command.upgrade(cfg, "head")

    head_revision = ScriptDirectory.from_config(cfg).get_current_head()
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        stamped = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()

    assert stamped == head_revision


def test_downgrade_to_base_clears_version_tracking(db_path: Path) -> None:
    cfg = _config()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar()

    assert count == 0
