"""Goal routes (docs/TASKS.md T096, docs/API_SPEC.md #1).

Thin HTTP adapter over `GoalApplicationService` (T065) -- no business
logic here, only request/response shaping and exception-to-HTTP-error
translation, same split as onboarding.py.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_goal_service
from app.api.errors import api_error
from app.domain.entities import LearningGoal
from app.domain.enums import GoalStatus, TargetLevel
from app.domain.value_objects import FiveLevelScale
from app.services.goal_service import (
    GoalApplicationService,
    GoalNotFoundError,
    InvalidGoalError,
    InvalidGoalTransitionError,
)

router = APIRouter(prefix="/api/v1/goals", tags=["goals"])

GoalServiceDep = Annotated[GoalApplicationService, Depends(get_goal_service)]


class CreateGoalRequest(BaseModel):
    title: str
    target_level: TargetLevel
    description: str | None = None
    domain: str | None = None
    priority: FiveLevelScale = 3
    deadline: datetime | None = None
    available_minutes_per_week: int | None = None


class GoalResponse(BaseModel):
    id: str
    title: str
    description: str | None
    domain: str | None
    target_level: TargetLevel
    status: GoalStatus
    priority: FiveLevelScale
    deadline: datetime | None
    available_minutes_per_week: int | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, goal: LearningGoal) -> "GoalResponse":
        return cls(**goal.model_dump())


class GoalListResponse(BaseModel):
    goals: list[GoalResponse]


@router.post("", response_model=GoalResponse, status_code=201)
def create_goal(request: CreateGoalRequest, service: GoalServiceDep) -> GoalResponse:
    try:
        goal = service.create_goal(
            title=request.title,
            target_level=request.target_level,
            description=request.description,
            domain=request.domain,
            priority=request.priority,
            deadline=request.deadline,
            available_minutes_per_week=request.available_minutes_per_week,
        )
    except InvalidGoalError as exc:
        raise api_error("VALIDATION_ERROR", str(exc), 400) from exc
    return GoalResponse.from_entity(goal)


@router.get("", response_model=GoalListResponse)
def list_goals(service: GoalServiceDep) -> GoalListResponse:
    return GoalListResponse(goals=[GoalResponse.from_entity(g) for g in service.list_goals()])


@router.get("/{goal_id}", response_model=GoalResponse)
def get_goal(goal_id: str, service: GoalServiceDep) -> GoalResponse:
    try:
        goal = service.get_goal(goal_id)
    except GoalNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Goal '{goal_id}' not found", 404) from exc
    return GoalResponse.from_entity(goal)


@router.post("/{goal_id}/pause", response_model=GoalResponse)
def pause_goal(goal_id: str, service: GoalServiceDep) -> GoalResponse:
    try:
        goal = service.pause_goal(goal_id)
    except GoalNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Goal '{goal_id}' not found", 404) from exc
    except InvalidGoalTransitionError as exc:
        raise api_error("SESSION_STATE_ERROR", str(exc), 409) from exc
    return GoalResponse.from_entity(goal)


@router.post("/{goal_id}/complete", response_model=GoalResponse)
def complete_goal(goal_id: str, service: GoalServiceDep) -> GoalResponse:
    try:
        goal = service.complete_goal(goal_id)
    except GoalNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Goal '{goal_id}' not found", 404) from exc
    except InvalidGoalTransitionError as exc:
        raise api_error("SESSION_STATE_ERROR", str(exc), 409) from exc
    return GoalResponse.from_entity(goal)
