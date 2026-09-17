"""Project tasks -- breaks a project's success criteria into
individually addressable, submittable tasks (docs/TASKS.md T093).

A `ProjectTask` has no dedicated table or entity anywhere in the docs
(see T092's note: the entity-relationship diagram mentions it,
docs/DOMAIN_MODEL.md never gives it fields) -- it is realized as an
`Activity` with `type=project_task`, inside a dedicated `Session` with
`mode=project` (both enum values already existed for exactly this).

Each of the project's `success_criteria` becomes one task, 1:1 -- T092's
project generation reuses `exercise_generator`, which returns only one
prompt and one success-criteria list, so there is no separate
AI-authored task breakdown to draw from, and a success criterion
already reads as a concrete, checkable unit of work. `Activity` has no
free-text field to hold a task's description (docs/DOMAIN_MODEL.md #13:
id, session_id, type, sequence, concept_ids, status), so the convention
is: task N's description is `project.success_criteria[N - 1]` --
`Activity.sequence` is assigned in the same order, 1-based, so it always
lines up.
"""

from dataclasses import dataclass

from app.domain.entities import Activity, Session
from app.domain.enums import (
    ActivityStatus,
    ActivityType,
    ProjectStatus,
    SessionMode,
    SessionStatus,
)
from app.domain.ports import (
    ActivityRepository,
    ClockPort,
    IdGeneratorPort,
    ProjectRepository,
    SessionRepository,
)


class ProjectNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class ProjectTasksResult:
    session: Session
    tasks: list[Activity]


class ProjectTaskService:
    def __init__(
        self,
        projects: ProjectRepository,
        sessions: SessionRepository,
        activities: ActivityRepository,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._projects = projects
        self._sessions = sessions
        self._activities = activities
        self._clock = clock
        self._ids = ids

    def create_tasks(self, project_id: str) -> ProjectTasksResult:
        project = self._projects.get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        now = self._clock.now()
        session = Session(
            id=self._ids.new_id("session"),
            goal_id=project.goal_id,
            mode=SessionMode.PROJECT,
            objective=project.title,
            status=SessionStatus.ACTIVE,
            started_at=now,
        )
        self._sessions.add(session)

        tasks: list[Activity] = []
        for sequence, _criterion in enumerate(project.success_criteria, start=1):
            activity = Activity(
                id=self._ids.new_id("activity"),
                session_id=session.id,
                type=ActivityType.PROJECT_TASK,
                sequence=sequence,
                concept_ids=project.concept_ids,
                status=ActivityStatus.PENDING,
            )
            self._activities.add(activity)
            tasks.append(activity)

        if project.status == ProjectStatus.PROPOSED:
            self._projects.update(project.model_copy(update={"status": ProjectStatus.ACTIVE}))

        return ProjectTasksResult(session=session, tasks=tasks)
