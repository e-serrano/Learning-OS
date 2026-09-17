"""Project generation -- proposes a practical, multi-concept project
(docs/TASKS.md T092, docs/DOMAIN_MODEL.md #14: Project).

No dedicated "project" AI role exists among AI_CONTRACTS.md's 7
contracts, so this reuses `exercise_generator` (T071) -- same precedent
as T089's transfer assessment -- with context merged across every
target concept (mirrors DiagnosticService's `_merged_context`, T066)
and a task instruction asking for a practical project rather than a
single exercise.

`ExerciseGeneratorResponse` has no `title` field (it wasn't designed for
open-ended, multi-day project briefs) -- `title` is derived from the
first line of the generated prompt, truncated to a reasonable length.
This is a known compromise: a dedicated project-generation contract
would fit better, but adding an 8th role to AI_CONTRACTS.md's closed set
of 7 is a bigger, riskier change than this MVP task calls for.
"""

from typing import Any

from app.ai.contracts import ExerciseGeneratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Project
from app.domain.enums import ProjectStatus
from app.domain.ports import ClockPort, GoalRepository, IdGeneratorPort, ProjectRepository
from app.services.context_builder import ContextBuilder, GoalNotFoundError

PROJECT_PROMPT_VERSION = "exercise_generator.v1"
MAX_TITLE_LENGTH = 80


def _derive_title(prompt: str) -> str:
    stripped = prompt.strip()
    first_line = stripped.splitlines()[0] if stripped else "Untitled project"
    return first_line[:MAX_TITLE_LENGTH]


class ProjectGenerationService:
    def __init__(
        self,
        goals: GoalRepository,
        context_builder: ContextBuilder,
        projects: ProjectRepository,
        orchestrator: AIOrchestrator,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._goals = goals
        self._context_builder = context_builder
        self._projects = projects
        self._orchestrator = orchestrator
        self._clock = clock
        self._ids = ids

    async def generate_project(self, goal_id: str, concept_ids: list[str]) -> Project:
        goal = self._goals.get(goal_id)
        if goal is None:
            raise GoalNotFoundError(goal_id)

        request = AIRequest(
            role="exercise_generator",
            prompt_version=PROJECT_PROMPT_VERSION,
            goal={"id": goal.id, "title": goal.title, "target_level": goal.target_level.value},
            context=self._merged_context(goal_id, concept_ids),
            task={
                "assessment_type": "project",
                "instruction": (
                    "Design a practical, multi-step project that exercises all "
                    "of the listed concepts together in a realistic scenario, "
                    "not a single short exercise."
                ),
                "concept_ids": concept_ids,
            },
        )
        response = await self._orchestrator.generate(request, ExerciseGeneratorResponse)
        assert isinstance(response, ExerciseGeneratorResponse)

        project = Project(
            id=self._ids.new_id("project"),
            goal_id=goal_id,
            title=_derive_title(response.prompt),
            objective=response.prompt,
            difficulty=response.difficulty,
            status=ProjectStatus.PROPOSED,
            concept_ids=concept_ids,
            success_criteria=response.success_criteria,
        )
        self._projects.add(project)
        return project

    def _merged_context(self, goal_id: str, concept_ids: list[str]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        goal_included = False
        for concept_id in concept_ids:
            for item in self._context_builder.build(goal_id, concept_id):
                if item["kind"] == "goal":
                    if goal_included:
                        continue
                    goal_included = True
                merged.append(item)
        return merged
