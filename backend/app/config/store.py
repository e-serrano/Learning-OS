import os
import tempfile
from pathlib import Path

from app.config.models import AppConfig


class ConfigStore:
    """File-backed store for AppConfig.

    Provisional persistence for onboarding (Phase 1), ahead of the SQLite
    engine bootstrapped in Phase 2. Writes are atomic: a temp file in the
    same directory is written, flushed, and swapped in with os.replace, so
    a crash mid-write never leaves a partial/corrupt config file.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> AppConfig:
        if not self._path.exists():
            return AppConfig()
        return AppConfig.model_validate_json(self._path.read_text(encoding="utf-8"))

    def save(self, config: AppConfig) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = config.model_dump_json(indent=2)

        fd, tmp_name = tempfile.mkstemp(
            dir=self._path.parent, prefix=f".{self._path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                tmp_file.write(payload)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            os.replace(tmp_name, self._path)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
