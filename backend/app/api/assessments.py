"""Assessment routes (docs/TASKS.md T105, docs/API_SPEC.md #8).

`assessment_id` in every URL is the scaffolding Activity's id, not a
new identifier (docs/TASKS.md T105 note, mirroring T103/T104's
precedent of the Activity being the addressable unit for a piece of
session content).

`/answer` calls `AssessmentFlowService` (wraps T90's
`AssessmentCompletionService.complete_assessment` unchanged, then closes
the mastery/review gap the raw completion service leaves open -- see
that module's docstring); `/complete` reuses T103's
`SessionApplicationService.complete_session` unchanged -- same "answer =
full grade, complete = close session" split T103 established, cited
directly by T104 and now this task as precedent.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.api.dependencies import (
    get_assessment_flow_service,
    get_assessment_session_service,
    get_session_service,
)
from app.domain.enums import ActivityStatus, ConceptStatus, ExerciseType, SessionStatus
from app.domain.value_objects import ConfidencePercent, FiveLevelScale
from app.services.assessment_flow_service import AssessmentFlowResult, AssessmentFlowService
from app.services.assessment_session_service import (
    ActivityNotAnAssessmentError,
    AssessmentNotFoundError,
    AssessmentSessionResult,
    AssessmentSessionService,
)
from app.services.context_builder import GoalNotFoundError
from app.services.next_activity_service import InactiveSessionError, SessionNotFoundError
from app.services.session_service import InvalidSessionTransitionError, SessionApplicationService

router = APIRouter(tags=["assessments"])

AssessmentSessionServiceDep = Annotated[
    AssessmentSessionService, Depends(get_assessment_session_service)
]
AssessmentFlowServiceDep = Annotated[AssessmentFlowService, Depends(get_assessment_flow_service)]
SessionServiceDep = Annotated[SessionApplicationService, Depends(get_session_service)]


def _error(code: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": {}}},
    )


def _not_found(assessment_id: str) -> HTTPException:
    return _error("NOT_FOUND", f"Assessment '{assessment_id}' not found", 404)


class CreateAssessmentRequest(BaseModel):
    concept_id: str


class AssessmentExerciseResponse(BaseModel):
    exercise_id: str
    type: ExerciseType
    difficulty: FiveLevelScale
    prompt: str
    success_criteria: list[str]
    hints: list[str]


class AssessmentResponse(BaseModel):
    assessment_id: str
    session_id: str
    goal_id: str
    concept_id: str
    status: ActivityStatus
    exercise: AssessmentExerciseResponse

    @classmethod
    def from_result(cls, result: AssessmentSessionResult) -> "AssessmentResponse":
        activity = result.activity
        exercise = result.exercise
        return cls(
            assessment_id=activity.id,
            session_id=result.session.id,
            goal_id=result.session.goal_id,
            concept_id=activity.concept_ids[0],
            status=activity.status,
            exercise=AssessmentExerciseResponse(
                exercise_id=exercise.id,
                type=exercise.type,
                difficulty=exercise.difficulty,
                prompt=exercise.prompt,
                success_criteria=exercise.success_criteria,
                hints=exercise.hints,
            ),
        )


class AnswerAssessmentRequest(BaseModel):
    answer: str
    confidence: ConfidencePercent


class AssessmentEvaluationResponse(BaseModel):
    id: str
    correctness: float
    reasoning: float
    completeness: float
    independence: float
    transfer: float
    misconceptions: list[str]
    feedback: str
    recommended_action: str


class AssessmentConceptUpdateResponse(BaseModel):
    concept_id: str
    mastery: float
    status: ConceptStatus


class AssessmentAnswerResponse(BaseModel):
    evaluation: AssessmentEvaluationResponse
    transfer_demonstrated: bool
    independence_demonstrated: bool
    updated_concepts: list[AssessmentConceptUpdateResponse]

    @classmethod
    def from_result(cls, result: AssessmentFlowResult) -> "AssessmentAnswerResponse":
        evaluation = result.completion.evaluation
        return cls(
            evaluation=AssessmentEvaluationResponse(
                id=evaluation.id,
                correctness=evaluation.correctness,
                reasoning=evaluation.reasoning,
                completeness=evaluation.completeness,
                independence=evaluation.independence,
                transfer=evaluation.transfer,
                misconceptions=evaluation.misconceptions,
                feedback=evaluation.feedback,
                recommended_action=evaluation.recommended_action,
            ),
            transfer_demonstrated=result.completion.transfer_demonstrated,
            independence_demonstrated=result.completion.independence_demonstrated,
            updated_concepts=[
                AssessmentConceptUpdateResponse(concept_id=c.id, mastery=c.mastery, status=c.status)
                for c in result.concepts
            ],
        )


class AssessmentCompleteResponse(BaseModel):
    session_id: str
    status: SessionStatus


@router.post(
    "/api/v1/goals/{goal_id}/assessments", response_model=AssessmentResponse, status_code=201
)
async def create_assessment(
    goal_id: str, request: CreateAssessmentRequest, service: AssessmentSessionServiceDep
) -> AssessmentResponse:
    try:
        result = await service.create_assessment(goal_id, request.concept_id)
    except GoalNotFoundError as exc:
        raise _error("NOT_FOUND", f"Goal '{goal_id}' not found", 404) from exc
    except AIInvalidOutputError as exc:
        raise _error("AI_INVALID_OUTPUT", str(exc), 422) from exc
    except AIProviderUnavailableError as exc:
        raise _error("AI_UNAVAILABLE", str(exc), 503) from exc
    return AssessmentResponse.from_result(result)


@router.get("/api/v1/assessments/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(assessment_id: str, service: AssessmentSessionServiceDep) -> AssessmentResponse:
    try:
        result = service.get_assessment(assessment_id)
    except (AssessmentNotFoundError, ActivityNotAnAssessmentError) as exc:
        raise _not_found(assessment_id) from exc
    return AssessmentResponse.from_result(result)


@router.post("/api/v1/assessments/{assessment_id}/answer", response_model=AssessmentAnswerResponse)
async def answer_assessment(
    assessment_id: str,
    request: AnswerAssessmentRequest,
    assessment_session: AssessmentSessionServiceDep,
    assessment_flow: AssessmentFlowServiceDep,
) -> AssessmentAnswerResponse:
    try:
        assessment = assessment_session.get_assessment(assessment_id)
    except (AssessmentNotFoundError, ActivityNotAnAssessmentError) as exc:
        raise _not_found(assessment_id) from exc

    try:
        result = await assessment_flow.complete_assessment(
            assessment.exercise.id,
            assessment.session.id,
            assessment_id,
            assessment.session.goal_id,
            request.answer,
            request.confidence,
        )
    except InactiveSessionError as exc:
        raise _error(
            "SESSION_STATE_ERROR", f"Session '{assessment.session.id}' is not active", 409
        ) from exc
    except AIInvalidOutputError as exc:
        raise _error("AI_INVALID_OUTPUT", str(exc), 422) from exc
    except AIProviderUnavailableError as exc:
        raise _error("AI_UNAVAILABLE", str(exc), 503) from exc

    return AssessmentAnswerResponse.from_result(result)


@router.post(
    "/api/v1/assessments/{assessment_id}/complete", response_model=AssessmentCompleteResponse
)
def complete_assessment(
    assessment_id: str,
    assessment_session: AssessmentSessionServiceDep,
    session_service: SessionServiceDep,
) -> AssessmentCompleteResponse:
    try:
        assessment = assessment_session.get_assessment(assessment_id)
    except (AssessmentNotFoundError, ActivityNotAnAssessmentError) as exc:
        raise _not_found(assessment_id) from exc

    try:
        session = session_service.complete_session(assessment.session.id)
    except SessionNotFoundError as exc:
        raise _error("NOT_FOUND", f"Session '{assessment.session.id}' not found", 404) from exc
    except InvalidSessionTransitionError as exc:
        raise _error("SESSION_STATE_ERROR", str(exc), 409) from exc

    return AssessmentCompleteResponse(session_id=session.id, status=session.status)
