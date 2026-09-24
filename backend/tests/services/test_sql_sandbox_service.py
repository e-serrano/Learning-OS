import pytest

from app.services.sql_sandbox_service import (
    MAX_SQL_LENGTH,
    MAX_STATEMENTS,
    SqlSandboxError,
    SqlSandboxService,
    _split_statements,
)


@pytest.fixture
def service() -> SqlSandboxService:
    return SqlSandboxService()


def test_runs_a_single_select(service: SqlSandboxService) -> None:
    result = service.run("SELECT 1 AS n, 'a' AS s")

    assert result.error is None
    assert result.columns == ["n", "s"]
    assert result.rows == [[1, "a"]]
    assert result.row_count == 1
    assert result.truncated is False


def test_runs_setup_statements_then_returns_the_final_select(
    service: SqlSandboxService,
) -> None:
    result = service.run(
        """
        CREATE TABLE t (id INTEGER, name TEXT);
        INSERT INTO t VALUES (1, 'a'), (2, 'b');
        SELECT id, name FROM t ORDER BY id;
        """
    )

    assert result.error is None
    assert result.columns == ["id", "name"]
    assert result.rows == [[1, "a"], [2, "b"]]
    assert result.statement_count == 3


def test_ddl_only_script_returns_no_rows_and_no_error(service: SqlSandboxService) -> None:
    result = service.run("CREATE TABLE t (id INTEGER)")

    assert result.error is None
    assert result.columns == []
    assert result.rows == []


def test_syntax_error_is_a_result_not_an_exception(service: SqlSandboxService) -> None:
    result = service.run("SELEKT 1")

    assert result.error is not None
    assert result.columns == []
    assert result.rows == []


def test_unknown_table_is_a_result_not_an_exception(service: SqlSandboxService) -> None:
    result = service.run("SELECT * FROM does_not_exist")

    assert result.error is not None


def test_attach_database_is_denied(service: SqlSandboxService) -> None:
    result = service.run("ATTACH DATABASE 'escape.db' AS escaped")

    assert result.error is not None
    assert "not authorized" in result.error.lower()


def test_each_run_gets_an_isolated_connection(service: SqlSandboxService) -> None:
    service.run("CREATE TABLE t (id INTEGER)")
    result = service.run("SELECT * FROM t")

    assert result.error is not None  # table from the previous run does not exist here


def test_blank_sql_is_rejected(service: SqlSandboxService) -> None:
    with pytest.raises(SqlSandboxError):
        service.run("   ")


def test_oversized_sql_is_rejected(service: SqlSandboxService) -> None:
    with pytest.raises(SqlSandboxError):
        service.run("SELECT " + "1" * MAX_SQL_LENGTH)


def test_too_many_statements_is_rejected(service: SqlSandboxService) -> None:
    with pytest.raises(SqlSandboxError):
        service.run(";".join("SELECT 1" for _ in range(MAX_STATEMENTS + 1)))


def test_result_is_truncated_beyond_max_rows(service: SqlSandboxService) -> None:
    result = service.run(
        "WITH RECURSIVE seq(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM seq WHERE n < 300) "
        "SELECT n FROM seq"
    )

    assert result.error is None
    assert result.truncated is True
    assert result.row_count == 200


class TestSplitStatements:
    def test_splits_on_top_level_semicolons(self) -> None:
        assert _split_statements("SELECT 1; SELECT 2") == ["SELECT 1", "SELECT 2"]

    def test_semicolon_inside_a_string_literal_is_not_a_boundary(self) -> None:
        statements = _split_statements("SELECT ';'; SELECT 2")
        assert statements == ["SELECT ';'", "SELECT 2"]

    def test_semicolon_inside_a_line_comment_is_not_a_boundary(self) -> None:
        statements = _split_statements("SELECT 1; -- a; b\nSELECT 2")
        assert statements == ["SELECT 1", "-- a; b\nSELECT 2"]

    def test_semicolon_inside_a_block_comment_is_not_a_boundary(self) -> None:
        statements = _split_statements("SELECT 1; /* a; b */ SELECT 2")
        assert statements == ["SELECT 1", "/* a; b */ SELECT 2"]

    def test_trailing_whitespace_and_empty_statements_are_dropped(self) -> None:
        assert _split_statements("SELECT 1;;  ") == ["SELECT 1"]

    def test_blank_input_yields_no_statements(self) -> None:
        assert _split_statements("   ") == []
