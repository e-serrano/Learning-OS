from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_sql_sandbox_service
from app.api.errors import api_error
from app.services.sql_sandbox_service import SqlSandboxError, SqlSandboxResult, SqlSandboxService

router = APIRouter(prefix="/api/v1/sandbox", tags=["sandbox"])

SqlSandboxServiceDep = Annotated[SqlSandboxService, Depends(get_sql_sandbox_service)]


class RunSqlRequest(BaseModel):
    sql: str


@router.post("/sql", response_model=SqlSandboxResult)
def run_sql(request: RunSqlRequest, service: SqlSandboxServiceDep) -> SqlSandboxResult:
    """Try-it console (docs/TASKS.md T137) -- runs the user's own SQL
    against a throwaway in-memory database, purely for their own
    feedback before answering. Never touches app state, never feeds
    evaluation. A malformed request (blank/oversized) is a 400; a SQL
    error from the query itself (bad syntax, unknown table) is a normal
    200 result with `error` set, same as a wrong quiz answer isn't an
    HTTP error."""
    try:
        return service.run(request.sql)
    except SqlSandboxError as exc:
        raise api_error("VALIDATION_ERROR", str(exc), 400) from exc
