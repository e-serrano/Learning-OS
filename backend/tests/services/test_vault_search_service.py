from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import VAULT_SEARCH_FTS_TABLE
from app.services.vault_search_service import InvalidSearchQueryError, VaultSearchService


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _index(engine: Engine, path: str, title: str, body: str) -> None:
    with engine.connect() as conn:
        conn.execute(
            text(f"INSERT INTO {VAULT_SEARCH_FTS_TABLE}(path, title, body) VALUES (:p, :t, :b)"),
            {"p": path, "t": title, "b": body},
        )
        conn.commit()


def test_search_finds_a_match_by_body_content(engine: Engine) -> None:
    _index(engine, "window_functions.md", "Window Functions", "Uses OVER() to rank rows.")
    _index(engine, "subqueries.md", "Subqueries", "A query nested inside another query.")
    service = VaultSearchService(engine)

    results = service.search("rank rows")

    assert len(results) == 1
    assert results[0].path == "window_functions.md"
    assert results[0].title == "Window Functions"


def test_search_finds_a_match_by_title(engine: Engine) -> None:
    _index(engine, "note.md", "Correlated Subqueries", "Some unrelated body text.")
    service = VaultSearchService(engine)

    results = service.search("correlated")

    assert len(results) == 1
    assert results[0].path == "note.md"


def test_search_returns_empty_list_when_nothing_matches(engine: Engine) -> None:
    _index(engine, "note.md", "Title", "Body content.")
    service = VaultSearchService(engine)

    assert service.search("nonexistent_term_xyz") == []


def test_search_rejects_a_blank_query(engine: Engine) -> None:
    service = VaultSearchService(engine)

    with pytest.raises(InvalidSearchQueryError):
        service.search("   ")


def test_search_treats_fts_operator_characters_as_literal_text(engine: Engine) -> None:
    """A query containing FTS5 syntax characters (quotes, `*`, `-`, `AND`)
    must never raise a syntax error -- it's user input, not a query
    language the user is expected to know (docs/TASKS.md T127). Whether it
    finds a match depends on tokenization of punctuation-only terms; what
    must always hold is that FTS5 never rejects the query outright."""
    _index(engine, "note.md", "Title", 'Weird body with "quotes" and AND OR NOT * - tokens.')
    service = VaultSearchService(engine)

    results = service.search('"quotes" AND OR NOT * -')

    assert isinstance(results, list)


def test_search_matches_words_in_any_order(engine: Engine) -> None:
    """Multiple words AND together rather than requiring an exact phrase
    match -- a query like "window sql" should still find a note that says
    "sql window", not just one with that exact substring."""
    _index(engine, "note.md", "Title", "Ranking rows with a window function in SQL.")
    service = VaultSearchService(engine)

    results = service.search("sql window")

    assert len(results) == 1


def test_search_respects_the_limit(engine: Engine) -> None:
    for i in range(5):
        _index(engine, f"note_{i}.md", f"Title {i}", "shared searchable term")
    service = VaultSearchService(engine)

    results = service.search("shared searchable term", limit=2)

    assert len(results) == 2


def test_search_snippet_highlights_the_matched_term(engine: Engine) -> None:
    _index(engine, "note.md", "Title", "This sentence contains the word banana inside it.")
    service = VaultSearchService(engine)

    results = service.search("banana")

    assert "[banana]" in results[0].snippet
