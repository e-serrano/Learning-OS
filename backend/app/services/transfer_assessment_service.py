"""Transfer assessment -- generates a novel application scenario for a
concept, explicitly avoiding a copy of any exercise already used for it
(docs/TASKS.md T089, docs/DOMAIN_MODEL.md #15: `AssessmentType.transfer`).

There is no dedicated "transfer" AI role among AI_CONTRACTS.md's 7
contracts, so this reuses `exercise_generator` (T071) -- but feeds prior
exercise prompts for this concept into `task` as content the AI must
not repeat, and explicitly asks for transfer to a new context rather
than a plain exercise.

No Assessment/AssessmentAttempt table exists -- same documented gap as
T066's diagnostic note (docs/DOMAIN_MODEL.md #15 describes the entity,
but docs/DATABASE_SCHEMA.md never got a table for it). The MVP doesn't
need one here either: the observable artifact is the generated Exercise
plus the Evidence T090 produces from grading it, not a separate
assessment record.
"""

from app.ai.contracts import ExerciseGeneratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Exercise
from app.domain.ports import ClockPort, ExerciseRepository, GoalRepository, IdGeneratorPort
from app.services.context_builder import ContextBuilder, GoalNotFoundError

TRANSFER_PROMPT_VERSION = "exercise_generator.v1"
MAX_PRIOR_EXERCISES = 5


class TransferAssessmentService:
    def __init__(
        self,
        goals: GoalRepository,
        context_builder: ContextBuilder,
        exercises: ExerciseRepository,
        orchestrator: AIOrchestrator,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._goals = goals
        self._context_builder = context_builder
        self._exercises = exercises
        self._orchestrator = orchestrator
        self._clock = clock
        self._ids = ids

    async def generate_transfer_scenario(self, goal_id: str, concept_id: str) -> Exercise:
        goal = self._goals.get(goal_id)
        if goal is None:
            raise GoalNotFoundError(goal_id)

        prior_prompts = [
            exercise.prompt
            for exercise in self._exercises.list_by_concept(concept_id)[:MAX_PRIOR_EXERCISES]
        ]

        request = AIRequest(
            role="exercise_generator",
            prompt_version=TRANSFER_PROMPT_VERSION,
            goal={"id": goal.id, "title": goal.title, "target_level": goal.target_level.value},
            context=self._context_builder.build(goal_id, concept_id),
            task={
                "concept_id": concept_id,
                "assessment_type": "transfer",
                "instruction": (
                    "Generate a new situation that requires transferring this "
                    "concept to a different context. Do not reuse or lightly "
                    "rephrase any of the prior exercises listed below."
                ),
                "prior_exercise_prompts": prior_prompts,
            },
        )
        response = await self._orchestrator.generate(request, ExerciseGeneratorResponse)
        assert isinstance(response, ExerciseGeneratorResponse)

        exercise = Exercise(
            id=self._ids.new_id("exercise"),
            type=response.type,
            difficulty=response.difficulty,
            goal_id=goal_id,
            concept_ids=[concept_id],
            prompt=response.prompt,
            success_criteria=response.success_criteria,
            hints=response.hints,
            solution=response.solution,
            common_mistakes=response.common_mistakes,
            transfer_variant=response.transfer_variant,
            created_at=self._clock.now(),
        )
        self._exercises.add(exercise)
        return exercise
