"""Boots a fresh backend for Playwright E2E runs (docs/TASKS.md T120):
deletes any stale E2E database, runs migrations, then starts uvicorn.

Cross-platform on purpose -- Playwright's `webServer` invokes this
identically from Windows (dev) and Linux (CI), and shell chaining like
`rm -rf x && uvicorn ...` doesn't work the same way in cmd.exe as it
does in sh, so both steps happen here in Python instead of in the
`webServer` command string.
"""

import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_ROOT / "data" / "e2e.sqlite3"


def main() -> None:
    for suffix in ("", "-wal", "-shm"):
        Path(f"{DB_PATH}{suffix}").unlink(missing_ok=True)

    env = os.environ.copy()
    env["LEARNINGOS_DB_PATH"] = str(DB_PATH)

    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"], check=True, cwd=BACKEND_ROOT, env=env
    )
    subprocess.run(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        check=True,
        cwd=BACKEND_ROOT,
        env=env,
    )


if __name__ == "__main__":
    sys.exit(main())
