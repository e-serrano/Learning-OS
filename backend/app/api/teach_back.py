"""Teach-back routes (docs/TASKS.md T133, docs/API_SPEC.md #6).

`teach_back_id` in every URL is the scaffolding Activity's id, not a new
identifier -- same precedent `api/assessments.py` (T105) established for
`assessment_id`. Answering and completing reuse the existing generic
session routes unchanged (`POST /sessions/{id}/activities/{id}/answer`,
`POST /sessions/{id}/complete`) -- see `teach_back_session_service.py`'s
docstring for why no dedicated answer/complete route is needed here,
unlike assessments.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.api.dependencies import get_teach_back_session_service
from app.api.errors import api_error
from app.domain.enums import ActivityStatus, ExerciseType
from app.domain.value_objects import FiveLevelScale
from app.services.context_builder import GoalNotFoundError
from app.services.teach_back_session_service import (
    ActivityNotATeachBackError,
    TeachBackNotFoundError,
    TeachBackSessionResult,
    TeachBackSessionService,
)

router = APIRouter(tags=["teach-back"])

TeachBackSessionServiceDep = Annotated[
    TeachBackSessionService, Depends(get_teach_back_session_service)
]


def _not_found(teach_back_id: str) -> Exception:
    return api_error("NOT_FOUND", f"Teach-back '{teach_back_id}' not found", 404)


class CreateTeachBackRequest(BaseModel):
    concept_id: str


class TeachBackExerciseResponse(BaseModel):
    exercise_id: str
    type: ExerciseType
    difficulty: FiveLevelScale
    prompt: str
    success_criteria: list[str]
    hints: list[str]


class TeachBackResponse(BaseModel):
    teach_back_id: str
    session_id: str
    goal_id: str
    concept_id: str
    status: ActivityStatus
    exercise: TeachBackExerciseResponse

    @classmethod
    def from_result(cls, result: TeachBackSessionResult) -> "TeachBackResponse":
        activity = result.activity
        exercise = result.exercise
        return cls(
            teach_back_id=activity.id,
            session_id=result.session.id,
            goal_id=result.session.goal_id,
            concept_id=activity.concept_ids[0],
            status=activity.status,
            exercise=TeachBackExerciseResponse(
                exercise_id=exercise.id,
                type=exercise.type,
                difficulty=exercise.difficulty,
                prompt=exercise.prompt,
                success_criteria=exercise.success_criteria,
                hints=exercise.hints,
            ),
        )


@router.post(
    "/api/v1/goals/{goal_id}/teach-back", response_model=TeachBackResponse, status_code=201
)
async def create_teach_back(
    goal_id: str, request: CreateTeachBackRequest, service: TeachBackSessionServiceDep
) -> TeachBackResponse:
    try:
        result = await service.create_teach_back(goal_id, request.concept_id)
    except GoalNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Goal '{goal_id}' not found", 404) from exc
    except AIInvalidOutputError as exc:
        raise api_error("AI_INVALID_OUTPUT", str(exc), 422) from exc
    except AIProviderUnavailableError as exc:
        raise api_error("AI_UNAVAILABLE", str(exc), 503) from exc
    return TeachBackResponse.from_result(result)


@router.get("/api/v1/teach-back/{teach_back_id}", response_model=TeachBackResponse)
def get_teach_back(teach_back_id: str, service: TeachBackSessionServiceDep) -> TeachBackResponse:
    try:
        result = service.get_teach_back(teach_back_id)
    except (TeachBackNotFoundError, ActivityNotATeachBackError) as exc:
        raise _not_found(teach_back_id) from exc
    return TeachBackResponse.from_result(result)
