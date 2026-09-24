"""Session routes (docs/TASKS.md T103, docs/API_SPEC.md #6).

`content` in `/next`'s response deliberately excludes `solution` and
`common_mistakes` -- showing the learner the answer (or the exact
mistakes to avoid) before they attempt the exercise would defeat the
exercise. Neither `API_SPEC.md` nor `AI_CONTRACTS.md` says so
explicitly; this is a judgment call made here, not inherited from a
prior task.

`/next` and the answer route's embedded `next_activity` both call
`ExerciseGeneratorService` (T071) through `ActivityContentService`
(T103), so both can raise `AIProviderUnavailableError`/
`AIInvalidOutputError` same as T101/T102's AI-calling routes.

`/tutor` (docs/TASKS.md T132, extended to `mode="interview"` by T141) is
a separate, stateless interactive turn using the Tutor AI role -- unlike
`/next`/`/answer`, it never touches `Activity`/`Evidence`/mastery. Only
usable on a `mode="socratic"` or `mode="interview"` session (`TutorService`
rejects any other mode); the caller resends the conversation-so-far each
call since nothing here persists it.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.ai.contracts import TutorResponse
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.api.dependencies import (
    get_activity_content_service,
    get_adaptive_activity_service,
    get_answer_flow_service,
    get_next_activity_service,
    get_session_service,
    get_tutor_service,
)
from app.api.errors import api_error
from app.domain.entities import Activity, Session
from app.domain.enums import ActivityType, ConceptStatus, ExerciseType, SessionMode, SessionStatus
from app.domain.value_objects import ConfidencePercent, FiveLevelScale
from app.services.activity_content_service import ActivityContent, ActivityContentService
from app.services.adaptive_activity_service import AdaptiveActivityService
from app.services.answer_flow_service import (
    ActivityHasNoExerciseError,
    ActivityNotFoundError,
    AnswerFlowService,
    AnswerResult,
)
from app.services.context_builder import ConceptNotFoundError, GoalNotFoundError
from app.services.next_activity_service import (
    InactiveSessionError,
    NextActivityService,
    NoActivityCandidatesError,
    SessionNotFoundError,
)
from app.services.session_service import (
    InvalidSessionError,
    InvalidSessionTransitionError,
    SessionApplicationService,
)
from app.services.tutor_service import SessionNotTutorableError, TutorService, TutorTurn

router = APIRouter(tags=["sessions"])

SessionServiceDep = Annotated[SessionApplicationService, Depends(get_session_service)]
NextActivityServiceDep = Annotated[NextActivityService, Depends(get_next_activity_service)]
AdaptiveActivityServiceDep = Annotated[
    AdaptiveActivityService, Depends(get_adaptive_activity_service)
]
ActivityContentServiceDep = Annotated[ActivityContentService, Depends(get_activity_content_service)]
AnswerFlowServiceDep = Annotated[AnswerFlowService, Depends(get_answer_flow_service)]
TutorServiceDep = Annotated[TutorService, Depends(get_tutor_service)]


class CreateSessionRequest(BaseModel):
    mode: SessionMode
    duration_minutes: int


class SessionResponse(BaseModel):
    id: str
    goal_id: str
    mode: SessionMode
    objective: str
    status: SessionStatus
    started_at: datetime | None
    ended_at: datetime | None


class ExerciseContentResponse(BaseModel):
    exercise_id: str
    type: ExerciseType
    difficulty: FiveLevelScale
    prompt: str
    success_criteria: list[str]
    hints: list[str]

    @classmethod
    def from_content(cls, content: ActivityContent) -> "ExerciseContentResponse":
        exercise = content.exercise
        return cls(
            exercise_id=exercise.id,
            type=exercise.type,
            difficulty=exercise.difficulty,
            prompt=exercise.prompt,
            success_criteria=exercise.success_criteria,
            hints=exercise.hints,
        )


class NextActivityResponse(BaseModel):
    activity_id: str
    type: ActivityType
    content: ExerciseContentResponse

    @classmethod
    def from_content(cls, content: ActivityContent) -> "NextActivityResponse":
        return cls(
            activity_id=content.activity.id,
            type=content.activity.type,
            content=ExerciseContentResponse.from_content(content),
        )


class EvaluationResponse(BaseModel):
    id: str
    correctness: float
    reasoning: float
    completeness: float
    independence: float
    transfer: float
    misconceptions: list[str]
    feedback: str
    recommended_action: str


class KnowledgeUpdateResponse(BaseModel):
    concept_id: str
    mastery: float
    status: ConceptStatus
    mistakes_recorded: int
    next_review_scheduled_at: datetime


class SubmitAnswerRequest(BaseModel):
    answer: str
    confidence: ConfidencePercent


class SubmitAnswerResponse(BaseModel):
    evaluation: EvaluationResponse
    knowledge_updates: list[KnowledgeUpdateResponse]
    next_activity: NextActivityResponse | None

    @classmethod
    def from_result(cls, result: AnswerResult) -> "SubmitAnswerResponse":
        evaluation = result.evaluation
        return cls(
            evaluation=EvaluationResponse(
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
            knowledge_updates=[
                KnowledgeUpdateResponse(
                    concept_id=u.concept_id,
                    mastery=u.mastery,
                    status=u.status,
                    mistakes_recorded=u.mistakes_recorded,
                    next_review_scheduled_at=u.next_review_scheduled_at,
                )
                for u in result.knowledge_updates
            ],
            next_activity=(
                NextActivityResponse.from_content(result.next_activity)
                if result.next_activity is not None
                else None
            ),
        )


class TutorTurnRequest(BaseModel):
    concept_id: str
    message: str = ""
    history: list[TutorTurn] = Field(default_factory=list)


class TutorTurnResponse(BaseModel):
    mode: str
    content: str
    check_for_understanding: str | None
    next_activity: str | None

    @classmethod
    def from_tutor_response(cls, response: TutorResponse) -> "TutorTurnResponse":
        return cls(
            mode=response.mode,
            content=response.content,
            check_for_understanding=response.check_for_understanding,
            next_activity=response.next_activity,
        )


def _session_response(session: Session) -> SessionResponse:
    return SessionResponse(**session.model_dump())


@router.post("/api/v1/goals/{goal_id}/sessions", response_model=SessionResponse)
def create_session(
    goal_id: str, request: CreateSessionRequest, service: SessionServiceDep
) -> SessionResponse:
    try:
        session = service.create_session(goal_id, request.mode, request.duration_minutes)
    except GoalNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Goal '{goal_id}' not found", 404) from exc
    except InvalidSessionError as exc:
        raise api_error("VALIDATION_ERROR", str(exc), 400) from exc
    return _session_response(session)


@router.get("/api/v1/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, service: SessionServiceDep) -> SessionResponse:
    try:
        session = service.get_session(session_id)
    except SessionNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Session '{session_id}' not found", 404) from exc
    return _session_response(session)


async def _pick_and_attach(
    goal_id: str, activity: Activity, activity_content: ActivityContentServiceDep
) -> ActivityContent:
    try:
        return await activity_content.attach_exercise(goal_id, activity)
    except AIInvalidOutputError as exc:
        raise api_error("AI_INVALID_OUTPUT", str(exc), 422) from exc
    except AIProviderUnavailableError as exc:
        raise api_error("AI_UNAVAILABLE", str(exc), 503) from exc


@router.post("/api/v1/sessions/{session_id}/next", response_model=NextActivityResponse)
async def next_activity(
    session_id: str,
    service: NextActivityServiceDep,
    activity_content: ActivityContentServiceDep,
    session_service: SessionServiceDep,
) -> NextActivityResponse:
    try:
        picked = service.select_next(session_id)
    except SessionNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Session '{session_id}' not found", 404) from exc
    except InactiveSessionError as exc:
        raise api_error(
            "SESSION_STATE_ERROR", f"Session '{session_id}' is not active", 409
        ) from exc
    except NoActivityCandidatesError as exc:
        raise api_error("SESSION_STATE_ERROR", "No activity candidates for this goal", 409) from exc

    session = session_service.get_session(session_id)
    content = await _pick_and_attach(session.goal_id, picked, activity_content)
    return NextActivityResponse.from_content(content)


@router.post("/api/v1/sessions/{session_id}/tutor", response_model=TutorTurnResponse)
async def tutor_turn(
    session_id: str, request: TutorTurnRequest, service: TutorServiceDep
) -> TutorTurnResponse:
    try:
        response = await service.ask(
            session_id, request.concept_id, request.history, request.message
        )
    except SessionNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Session '{session_id}' not found", 404) from exc
    except (GoalNotFoundError, ConceptNotFoundError) as exc:
        raise api_error("NOT_FOUND", str(exc), 404) from exc
    except InactiveSessionError as exc:
        raise api_error(
            "SESSION_STATE_ERROR", f"Session '{session_id}' is not active", 409
        ) from exc
    except SessionNotTutorableError as exc:
        raise api_error(
            "SESSION_STATE_ERROR",
            f"Session '{session_id}' is not in socratic or interview mode",
            409,
        ) from exc
    except AIInvalidOutputError as exc:
        raise api_error("AI_INVALID_OUTPUT", str(exc), 422) from exc
    except AIProviderUnavailableError as exc:
        raise api_error("AI_UNAVAILABLE", str(exc), 503) from exc
    return TutorTurnResponse.from_tutor_response(response)


@router.post(
    "/api/v1/sessions/{session_id}/activities/{activity_id}/answer",
    response_model=SubmitAnswerResponse,
)
async def submit_answer(
    session_id: str,
    activity_id: str,
    request: SubmitAnswerRequest,
    service: AnswerFlowServiceDep,
) -> SubmitAnswerResponse:
    try:
        result = await service.submit_answer(
            session_id, activity_id, request.answer, request.confidence
        )
    except SessionNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Session '{session_id}' not found", 404) from exc
    except ActivityNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Activity '{activity_id}' not found", 404) from exc
    except ActivityHasNoExerciseError as exc:
        raise api_error(
            "SESSION_STATE_ERROR",
            f"Activity '{activity_id}' has no exercise yet -- call /next first",
            409,
        ) from exc
    except AIInvalidOutputError as exc:
        raise api_error("AI_INVALID_OUTPUT", str(exc), 422) from exc
    except AIProviderUnavailableError as exc:
        raise api_error("AI_UNAVAILABLE", str(exc), 503) from exc
    return SubmitAnswerResponse.from_result(result)


@router.post("/api/v1/sessions/{session_id}/complete", response_model=SessionResponse)
def complete_session(session_id: str, service: SessionServiceDep) -> SessionResponse:
    try:
        session = service.complete_session(session_id)
    except SessionNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Session '{session_id}' not found", 404) from exc
    except InvalidSessionTransitionError as exc:
        raise api_error("SESSION_STATE_ERROR", str(exc), 409) from exc
    return _session_response(session)
