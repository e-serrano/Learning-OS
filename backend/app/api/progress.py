"""Progress route (docs/TASKS.md T107, docs/API_SPEC.md #10).

Thin HTTP adapter over `ProgressService` -- see that module's docstring
for the judgment calls behind `mastery`'s normalization, `due_reviews`'
goal filtering, and `recent_sessions`' window.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_progress_service
from app.services.context_builder import GoalNotFoundError
from app.services.progress_service import GoalProgress, ProgressService

router = APIRouter(tags=["progress"])

ProgressServiceDep = Annotated[ProgressService, Depends(get_progress_service)]


def _error(code: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": {}}},
    )


class ProgressResponse(BaseModel):
    mastery: float
    concepts_total: int
    mastered: int
    weak: int
    due_reviews: int
    recent_sessions: int

    @classmethod
    def from_result(cls, result: GoalProgress) -> "ProgressResponse":
        return cls(
            mastery=result.mastery,
            concepts_total=result.concepts_total,
            mastered=result.mastered,
            weak=result.weak,
            due_reviews=result.due_reviews,
            recent_sessions=result.recent_sessions,
        )


@router.get("/api/v1/goals/{goal_id}/progress", response_model=ProgressResponse)
def get_progress(goal_id: str, service: ProgressServiceDep) -> ProgressResponse:
    try:
        result = service.get_progress(goal_id)
    except GoalNotFoundError as exc:
        raise _error("NOT_FOUND", f"Goal '{goal_id}' not found", 404) from exc
    return ProgressResponse.from_result(result)
