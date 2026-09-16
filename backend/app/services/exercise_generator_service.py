"""Exercise generator -- turns a concept into a persisted Exercise
(docs/TASKS.md T071, docs/AI_CONTRACTS.md #7: type, difficulty, prompt,
success criteria, hints, solution, common mistakes, transfer variant).

AI proposes exercise content; identity and associations (id, goal_id,
concept_ids) are assigned by this service, never by the model
(docs/AGENTS.md #5: AI output never directly mutates application state).
"""

from app.ai.contracts import ExerciseGeneratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Exercise
from app.domain.ports import ClockPort, ExerciseRepository, GoalRepository, IdGeneratorPort
from app.services.context_builder import ContextBuilder, GoalNotFoundError

EXERCISE_GENERATOR_PROMPT_VERSION = "exercise_generator.v1"


class ExerciseGeneratorService:
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

    async def generate(self, goal_id: str, concept_id: str) -> Exercise:
        goal = self._goals.get(goal_id)
        if goal is None:
            raise GoalNotFoundError(goal_id)

        request = AIRequest(
            role="exercise_generator",
            prompt_version=EXERCISE_GENERATOR_PROMPT_VERSION,
            goal={"id": goal.id, "title": goal.title, "target_level": goal.target_level.value},
            context=self._context_builder.build(goal_id, concept_id),
            task={"concept_id": concept_id},
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
