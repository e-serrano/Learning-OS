"""Project submission -- registers a deliverable for a project task as
evidence (docs/TASKS.md T094, docs/API_SPEC.md #9:
`POST /projects/{project_id}/tasks/{task_id}/submit`).

Grading it (independence, transfer) is a separate, later concern (T095)
-- this mirrors the same submit-then-evaluate split already used for
exercises (AnswerSubmissionService/T072 vs EvaluatorService/T073):
marks the task `Activity` completed and records an unscored Evidence
row per concept (all score fields `None` except `difficulty`) as the
audit trail that a deliverable was submitted. `MasteryEngine` (T061)
already treats `None` score fields as "no signal" and skips them, so
this evidence is inert until T095 adds a second, scored Evidence row
for the same concept -- it never skews mastery on its own.

The deliverable text has nowhere else to live: `Activity` has no
free-text field (same gap noted in T093), so it goes into
`Evidence.metadata`, the same place diagnostic/review answers already
go (T066, T087).
"""

from dataclasses import dataclass

from app.domain.entities import Activity, Evidence
from app.domain.enums import ActivityStatus, ActivityType, EvidenceSourceType
from app.domain.ports import (
    ActivityRepository,
    ClockPort,
    EvidenceRepository,
    IdGeneratorPort,
    ProjectRepository,
)


class ProjectNotFoundError(Exception):
    pass


class TaskNotFoundError(Exception):
    pass


class NotAProjectTaskError(Exception):
    pass


@dataclass(frozen=True)
class ProjectSubmissionResult:
    task: Activity
    evidence: list[Evidence]


class ProjectSubmissionService:
    def __init__(
        self,
        projects: ProjectRepository,
        activities: ActivityRepository,
        evidence: EvidenceRepository,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._projects = projects
        self._activities = activities
        self._evidence = evidence
        self._clock = clock
        self._ids = ids

    def submit_task(
        self, project_id: str, task_id: str, deliverable: str
    ) -> ProjectSubmissionResult:
        project = self._projects.get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)
        task = self._activities.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        if task.type != ActivityType.PROJECT_TASK:
            raise NotAProjectTaskError(task_id)

        completed_task = task.model_copy(update={"status": ActivityStatus.COMPLETED})
        self._activities.update(completed_task)

        now = self._clock.now()
        concept_ids = task.concept_ids or project.concept_ids
        created: list[Evidence] = []
        for concept_id in concept_ids:
            record = Evidence(
                id=self._ids.new_id("evidence"),
                concept_id=concept_id,
                goal_id=project.goal_id,
                session_id=task.session_id,
                activity_id=task.id,
                source_type=EvidenceSourceType.PROJECT,
                difficulty=project.difficulty,
                timestamp=now,
                metadata={
                    "deliverable": deliverable,
                    "project_id": project_id,
                    "task_id": task_id,
                },
            )
            self._evidence.add(record)
            created.append(record)

        return ProjectSubmissionResult(task=completed_task, evidence=created)
