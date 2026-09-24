from fastapi.testclient import TestClient

from app.main import app


def test_run_sql_returns_columns_and_rows() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/sandbox/sql", json={"sql": "SELECT 1 AS n"})

    assert response.status_code == 200
    body = response.json()
    assert body["columns"] == ["n"]
    assert body["rows"] == [[1]]
    assert body["error"] is None


def test_run_sql_reports_a_query_error_as_a_normal_200() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/sandbox/sql", json={"sql": "SELEKT 1"})

    assert response.status_code == 200
    assert response.json()["error"] is not None


def test_run_sql_rejects_blank_sql_with_400() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/sandbox/sql", json={"sql": "   "})

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "VALIDATION_ERROR"


def test_two_runs_do_not_share_state(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Each call gets its own throwaway `:memory:` connection -- a table
    created in one run must not exist in the next, proving isolation
    through the real HTTP route, not just at the service layer."""
    client = TestClient(app)

    client.post("/api/v1/sandbox/sql", json={"sql": "CREATE TABLE t (id INTEGER)"})
    response = client.post("/api/v1/sandbox/sql", json={"sql": "SELECT * FROM t"})

    assert response.status_code == 200
    assert response.json()["error"] is not None
