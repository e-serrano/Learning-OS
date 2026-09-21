"""Diagnostic routes (docs/TASKS.md T102, docs/API_SPEC.md #5).

No request body: `API_SPEC.md` #5 documents none, so every concept
currently linked to the goal is diagnosed -- see
`DiagnosticSessionService`'s own docstring for why that only makes
sense once a roadmap (T101) has populated them.
"""

from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.api.dependencies import get_diagnostic_session_service
from app.api.errors import api_error
from app.domain.enums import SessionStatus
from app.services.context_builder import GoalNotFoundError
from app.services.diagnostic_session_service import (
    DiagnosticSessionResult,
    DiagnosticSessionService,
    NoConceptsForGoalError,
)

router = APIRouter(prefix="/api/v1/goals/{goal_id}/diagnostic", tags=["diagnostic"])

DiagnosticSessionServiceDep = Annotated[
    DiagnosticSessionService, Depends(get_diagnostic_session_service)
]


class DiagnosticItemResponse(BaseModel):
    activity_id: str
    concept_id: str
    evidence_type: Literal["recall", "application", "transfer"]
    question: str
    difficulty: int


class DiagnosticSessionResponse(BaseModel):
    session_id: str
    goal_id: str
    status: SessionStatus
    items: list[DiagnosticItemResponse]

    @classmethod
    def from_result(cls, result: DiagnosticSessionResult) -> "DiagnosticSessionResponse":
        return cls(
            session_id=result.session.id,
            goal_id=result.session.goal_id,
            status=result.session.status,
            items=[DiagnosticItemResponse(**asdict(item)) for item in result.items],
        )


@router.post("/start", response_model=DiagnosticSessionResponse)
async def start_diagnostic(
    goal_id: str, service: DiagnosticSessionServiceDep
) -> DiagnosticSessionResponse:
    try:
        result = await service.start_diagnostic(goal_id)
    except GoalNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Goal '{goal_id}' not found", 404) from exc
    except NoConceptsForGoalError as exc:
        raise api_error(
            "SESSION_STATE_ERROR",
            f"Goal '{goal_id}' has no concepts yet -- generate a roadmap first",
            409,
        ) from exc
    except AIInvalidOutputError as exc:
        raise api_error("AI_INVALID_OUTPUT", str(exc), 422) from exc
    except AIProviderUnavailableError as exc:
        raise api_error("AI_UNAVAILABLE", str(exc), 503) from exc
    return DiagnosticSessionResponse.from_result(result)
