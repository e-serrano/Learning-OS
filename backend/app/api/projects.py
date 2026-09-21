"""Project routes (docs/TASKS.md T106, docs/API_SPEC.md #9).

`POST /goals/{goal_id}/projects` combines T092 (generate) + T093
(create tasks) into one call -- see `project_session_service.py`'s
docstring for why. `POST /projects/{id}/tasks/{task_id}/submit`
combines T094 (submit) + T095 (evaluate) into the single route the spec
documents, then closes the mastery/review gap those two leave open --
see `project_flow_service.py`'s docstring.

`GET /projects/{project_id}` returns only the Project's own persisted
fields, not its tasks -- there is no persisted Project -> Session link
to resolve them from (see `project_session_service.py`); the client
keeps the `task_id`s handed back by the creation response.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.api.dependencies import get_project_flow_service, get_project_session_service
from app.domain.entities import Project
from app.domain.enums import ActivityStatus, ConceptStatus, ProjectStatus
from app.domain.value_objects import FiveLevelScale
from app.services.project_flow_service import ProjectFlowService, ProjectSubmissionFlowResult
from app.services.project_session_service import (
    GoalNotFoundError,
    ProjectCreationResult,
    ProjectNotFoundError,
    ProjectSessionService,
)
from app.services.project_submission_service import (
    NotAProjectTaskError,
    TaskNotFoundError,
)
from app.services.project_submission_service import (
    ProjectNotFoundError as ProjectSubmissionNotFoundError,
)

router = APIRouter(tags=["projects"])

ProjectSessionServiceDep = Annotated[ProjectSessionService, Depends(get_project_session_service)]
ProjectFlowServiceDep = Annotated[ProjectFlowService, Depends(get_project_flow_service)]


def _error(code: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": {}}},
    )


def _project_not_found(project_id: str) -> HTTPException:
    return _error("NOT_FOUND", f"Project '{project_id}' not found", 404)


class CreateProjectRequest(BaseModel):
    concept_ids: list[str]


class ProjectResponse(BaseModel):
    id: str
    goal_id: str
    title: str
    objective: str
    difficulty: FiveLevelScale
    status: ProjectStatus
    concept_ids: list[str]
    success_criteria: list[str]
    artifact_path: str | None

    @classmethod
    def from_entity(cls, project: Project) -> "ProjectResponse":
        return cls(**project.model_dump())


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]


class ProjectTaskResponse(BaseModel):
    task_id: str
    sequence: int
    description: str
    status: ActivityStatus


class CreateProjectResponse(BaseModel):
    project: ProjectResponse
    session_id: str
    tasks: list[ProjectTaskResponse]

    @classmethod
    def from_result(cls, result: ProjectCreationResult) -> "CreateProjectResponse":
        criteria = result.project.success_criteria
        return cls(
            project=ProjectResponse.from_entity(result.project),
            session_id=result.session.id,
            tasks=[
                ProjectTaskResponse(
                    task_id=task.id,
                    sequence=task.sequence,
                    description=criteria[task.sequence - 1]
                    if task.sequence - 1 < len(criteria)
                    else "",
                    status=task.status,
                )
                for task in result.tasks
            ],
        )


class SubmitTaskRequest(BaseModel):
    deliverable: str


class ProjectTaskEvaluationResponse(BaseModel):
    correctness: float
    reasoning: float
    independence: float
    transfer: float
    feedback: str
    misconceptions: list[str]


class ProjectConceptUpdateResponse(BaseModel):
    concept_id: str
    mastery: float
    status: ConceptStatus


class SubmitTaskResponse(BaseModel):
    task_id: str
    task_status: ActivityStatus
    evaluation: ProjectTaskEvaluationResponse | None
    updated_concepts: list[ProjectConceptUpdateResponse]

    @classmethod
    def from_result(cls, result: ProjectSubmissionFlowResult) -> "SubmitTaskResponse":
        evaluation = None
        if result.evaluation_evidence:
            first = result.evaluation_evidence[0]
            metadata = first.metadata
            evaluation = ProjectTaskEvaluationResponse(
                correctness=first.correctness or 0.0,
                reasoning=first.reasoning or 0.0,
                independence=first.independence or 0.0,
                transfer=first.transfer or 0.0,
                feedback=metadata.get("feedback", ""),
                misconceptions=metadata.get("misconceptions", []),
            )
        return cls(
            task_id=result.task.id,
            task_status=result.task.status,
            evaluation=evaluation,
            updated_concepts=[
                ProjectConceptUpdateResponse(concept_id=c.id, mastery=c.mastery, status=c.status)
                for c in result.concepts
            ],
        )


@router.post(
    "/api/v1/goals/{goal_id}/projects", response_model=CreateProjectResponse, status_code=201
)
async def create_project(
    goal_id: str, request: CreateProjectRequest, service: ProjectSessionServiceDep
) -> CreateProjectResponse:
    try:
        result = await service.create_project(goal_id, request.concept_ids)
    except GoalNotFoundError as exc:
        raise _error("NOT_FOUND", f"Goal '{goal_id}' not found", 404) from exc
    except AIInvalidOutputError as exc:
        raise _error("AI_INVALID_OUTPUT", str(exc), 422) from exc
    except AIProviderUnavailableError as exc:
        raise _error("AI_UNAVAILABLE", str(exc), 503) from exc
    return CreateProjectResponse.from_result(result)


@router.get("/api/v1/goals/{goal_id}/projects", response_model=ProjectListResponse)
def list_projects(goal_id: str, service: ProjectSessionServiceDep) -> ProjectListResponse:
    try:
        projects = service.list_projects(goal_id)
    except GoalNotFoundError as exc:
        raise _error("NOT_FOUND", f"Goal '{goal_id}' not found", 404) from exc
    return ProjectListResponse(projects=[ProjectResponse.from_entity(p) for p in projects])


@router.get("/api/v1/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, service: ProjectSessionServiceDep) -> ProjectResponse:
    try:
        project = service.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise _project_not_found(project_id) from exc
    return ProjectResponse.from_entity(project)


@router.post(
    "/api/v1/projects/{project_id}/tasks/{task_id}/submit", response_model=SubmitTaskResponse
)
async def submit_task(
    project_id: str,
    task_id: str,
    request: SubmitTaskRequest,
    project_session: ProjectSessionServiceDep,
    project_flow: ProjectFlowServiceDep,
) -> SubmitTaskResponse:
    try:
        project = project_session.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise _project_not_found(project_id) from exc

    try:
        result = await project_flow.submit_task(
            project_id, task_id, project.goal_id, request.deliverable
        )
    except ProjectSubmissionNotFoundError as exc:
        raise _project_not_found(project_id) from exc
    except TaskNotFoundError as exc:
        raise _error("NOT_FOUND", f"Task '{task_id}' not found", 404) from exc
    except NotAProjectTaskError as exc:
        raise _error("VALIDATION_ERROR", str(exc), 400) from exc
    except AIInvalidOutputError as exc:
        raise _error("AI_INVALID_OUTPUT", str(exc), 422) from exc
    except AIProviderUnavailableError as exc:
        raise _error("AI_UNAVAILABLE", str(exc), 503) from exc

    return SubmitTaskResponse.from_result(result)
