"""Project creation/list/lookup (docs/TASKS.md T106, docs/API_SPEC.md
#9: `POST /goals/{goal_id}/projects`, `GET /goals/{goal_id}/projects`,
`GET /projects/{project_id}`).

`POST /goals/{goal_id}/projects` combines T092
(`ProjectGenerationService.generate_project`) and T093
(`ProjectTaskService.create_tasks`) into one HTTP action -- API_SPEC.md
#9 has no separate "generate tasks" route, so a project is proposed and
broken into submittable tasks in the same call, same combining pattern
T102's diagnostic route already applies to session+items.

No persisted link from `Project` to the `Session` that `create_tasks`
makes for it (`DOMAIN_MODEL.md` #14 gives `Project` no `session_id`
field) -- `GET /projects/{project_id}` therefore returns only the
Project's own persisted fields, not its tasks; the client holds onto
the `task_id`s from the creation response, same as it already holds
`activity_id`s from T103's `/next` response for the rest of a session.
Inventing a `Project.session_id` column purely to support a
tasks-relisting endpoint the spec never asks for would be a bigger
change than this task calls for.
"""

from dataclasses import dataclass

from app.domain.entities import Activity, Project, Session
from app.domain.ports import GoalRepository, ProjectRepository
from app.services.context_builder import GoalNotFoundError
from app.services.project_generation_service import ProjectGenerationService
from app.services.project_task_service import ProjectNotFoundError, ProjectTaskService

__all__ = [
    "GoalNotFoundError",
    "ProjectCreationResult",
    "ProjectNotFoundError",
    "ProjectSessionService",
]


@dataclass(frozen=True)
class ProjectCreationResult:
    project: Project
    session: Session
    tasks: list[Activity]


class ProjectSessionService:
    def __init__(
        self,
        goals: GoalRepository,
        projects: ProjectRepository,
        generation: ProjectGenerationService,
        tasks: ProjectTaskService,
    ) -> None:
        self._goals = goals
        self._projects = projects
        self._generation = generation
        self._tasks = tasks

    async def create_project(self, goal_id: str, concept_ids: list[str]) -> ProjectCreationResult:
        project = await self._generation.generate_project(goal_id, concept_ids)
        tasks_result = self._tasks.create_tasks(project.id)

        activated = self._projects.get(project.id)
        assert activated is not None
        return ProjectCreationResult(
            project=activated, session=tasks_result.session, tasks=tasks_result.tasks
        )

    def list_projects(self, goal_id: str) -> list[Project]:
        if self._goals.get(goal_id) is None:
            raise GoalNotFoundError(goal_id)
        return self._projects.list_by_goal(goal_id)

    def get_project(self, project_id: str) -> Project:
        project = self._projects.get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)
        return project
