"""In-memory SQL "try it" console (docs/TASKS.md T137, user request).

Scoped deliberately narrow after `AskUserQuestion` (2026-09-24): this
runs only the user's own SQL, purely for their own informational
feedback before answering an exercise -- it never feeds evaluation
(docs/AGENTS.md #9: mastery/scoring stays AI-evaluation-derived, never
a side effect of whether a query happened to run) and it never executes
anything but SQL (no general-purpose/multi-language code execution,
no containers -- docs/AGENTS.md #25: smallest deterministic
implementation).

Every run gets its own throwaway `:memory:` SQLite connection -- never
the application's own engine, never a file on disk, discarded after the
call returns. The one remaining filesystem-escape vector for otherwise
in-memory SQL is `ATTACH DATABASE 'path' AS name`, which a plain
`:memory:` connection does not block on its own -- denied explicitly via
`sqlite3`'s authorizer callback. Extension loading (`load_extension`,
arbitrary native code) is never enabled, so it stays unavailable by
default. A wall-clock timeout guards against a pathological query (e.g.
an exploding recursive CTE) hanging the request.
"""

import sqlite3
import threading

from pydantic import BaseModel, Field

MAX_SQL_LENGTH = 20_000
MAX_STATEMENTS = 50
MAX_ROWS = 200
TIMEOUT_SECONDS = 5.0

SqlCell = str | int | float | None


class SqlSandboxError(ValueError):
    pass


class SqlSandboxResult(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[list[SqlCell]] = Field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    statement_count: int = 0
    error: str | None = None


def _split_statements(sql: str) -> list[str]:
    """Splits on top-level `;` only -- one inside a quoted string or a
    `--`/`/* */` comment never counts as a statement boundary."""
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            while i < n:
                buf.append(sql[i])
                if sql[i] == quote:
                    if i + 1 < n and sql[i + 1] == quote:  # doubled-quote escape
                        buf.append(sql[i + 1])
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue
        if sql[i : i + 2] == "--":
            while i < n and sql[i] != "\n":
                buf.append(sql[i])
                i += 1
            continue
        if sql[i : i + 2] == "/*":
            end = sql.find("*/", i + 2)
            end = end + 2 if end != -1 else n
            buf.append(sql[i:end])
            i = end
            continue
        if ch == ";":
            statements.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return [s for s in (stmt.strip() for stmt in statements) if s]


def _cell(value: object) -> SqlCell:
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if isinstance(value, str | int | float) or value is None:
        return value
    return str(value)


def _authorizer(action: int, *_args: object) -> int:
    if action == sqlite3.SQLITE_ATTACH:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


class SqlSandboxService:
    def run(self, sql: str) -> SqlSandboxResult:
        sql = sql.strip()
        if not sql:
            raise SqlSandboxError("SQL must not be blank")
        if len(sql) > MAX_SQL_LENGTH:
            raise SqlSandboxError(f"SQL exceeds {MAX_SQL_LENGTH} characters")

        statements = _split_statements(sql)
        if not statements:
            raise SqlSandboxError("SQL must not be blank")
        if len(statements) > MAX_STATEMENTS:
            raise SqlSandboxError(f"SQL exceeds {MAX_STATEMENTS} statements")

        conn = sqlite3.connect(":memory:")
        conn.set_authorizer(_authorizer)
        timer = threading.Timer(TIMEOUT_SECONDS, conn.interrupt)
        timer.start()
        try:
            cur = conn.cursor()
            columns: list[str] = []
            fetched: list[tuple[object, ...]] = []
            for statement in statements:
                cur.execute(statement)
                if cur.description is not None:
                    columns = [d[0] for d in cur.description]
                    fetched = cur.fetchmany(MAX_ROWS + 1)
                else:
                    columns = []
                    fetched = []
            conn.commit()
        except sqlite3.Error as exc:
            timed_out = isinstance(exc, sqlite3.OperationalError) and "interrupted" in str(exc)
            message = f"Query timed out after {TIMEOUT_SECONDS:g}s" if timed_out else str(exc)
            return SqlSandboxResult(statement_count=len(statements), error=message)
        finally:
            timer.cancel()
            conn.close()

        truncated = len(fetched) > MAX_ROWS
        rows = [[_cell(v) for v in row] for row in fetched[:MAX_ROWS]]
        return SqlSandboxResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            statement_count=len(statements),
        )
