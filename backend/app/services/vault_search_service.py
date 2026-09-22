"""Vault full-text search (docs/TASKS.md T127, docs/API_SPEC.md #2's
sibling: `GET /vault/search`).

Queries `vault_files_fts` (`app/persistence/models/vault_search.py`),
kept current by `VaultIndexer.reindex()` on every vault scan. A blank
query is rejected rather than treated as "match everything" -- FTS5's
own `MATCH` has no such meaning for an empty string, and "browse every
note" is a different feature (already served by `GET /vault/changes`
for pending changes, or a vault scan summary) than search.
"""

from dataclasses import dataclass

from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError

from app.persistence.models import VAULT_SEARCH_FTS_TABLE

DEFAULT_LIMIT = 20
SNIPPET_ELLIPSIS = "..."


class InvalidSearchQueryError(ValueError):
    pass


@dataclass(frozen=True)
class VaultSearchResult:
    path: str
    title: str
    snippet: str


class VaultSearchService:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def search(self, query: str, limit: int = DEFAULT_LIMIT) -> list[VaultSearchResult]:
        stripped = query.strip()
        if not stripped:
            raise InvalidSearchQueryError("query must not be blank")

        # Quoting each whitespace-separated token as its own FTS5 phrase
        # treats operator characters (`"`, `*`, `-`, `AND`/`OR`/`NOT`) in
        # user input as plain text to match, not query syntax to parse -- a
        # query the user typed should never be able to make FTS5 itself
        # raise a syntax error. Space-separated quoted phrases still AND
        # together (FTS5's default), so "sql window" still matches a note
        # containing both words in either order -- only each *token* is
        # literal, not the whole query.
        fts_query = " ".join(f'"{token.replace('"', '""')}"' for token in stripped.split())

        try:
            with self._engine.connect() as conn:
                rows = conn.execute(
                    text(
                        f"SELECT path, title, "  # noqa: S608 -- table name is our own constant
                        f"snippet({VAULT_SEARCH_FTS_TABLE}, 2, '[', ']', '{SNIPPET_ELLIPSIS}', 12) "
                        f"AS snippet "
                        f"FROM {VAULT_SEARCH_FTS_TABLE} "
                        f"WHERE {VAULT_SEARCH_FTS_TABLE} MATCH :query "
                        f"ORDER BY rank LIMIT :limit"
                    ),
                    {"query": fts_query, "limit": limit},
                ).all()
        except OperationalError as exc:
            raise InvalidSearchQueryError(str(exc)) from exc

        return [
            VaultSearchResult(path=row.path, title=row.title, snippet=row.snippet) for row in rows
        ]
