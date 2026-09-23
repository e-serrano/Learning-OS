"""Teach-back prompt generation (docs/TASKS.md T133): asks the learner to
explain a concept in their own words as if teaching someone else, rather
than solve a normal exercise.

Sibling of `TransferAssessmentService` (T089): no dedicated "teach-back"
AI role exists among `AI_CONTRACTS.md`'s 7 contracts, so this reuses
`exercise_generator` (T071) the same way, biasing `task` with an explicit
instruction instead of inventing a new contract.

Unlike `TransferAssessmentService`, which leaves the generated exercise's
`type` entirely up to the model (a transfer scenario can legitimately be
any `ExerciseType`), this forces the persisted `Exercise.type` to
`ExerciseType.TEACH_BACK` regardless of what the model returned. A
teach-back call has exactly one `ExerciseType` it is meant to produce, so
the application enforcing that classification -- content stays the
model's proposal, but "is this a teach-back exercise" is a structural
guarantee the caller (and `EvidenceCreationService`'s type-aware
`source_type`, T133) can rely on rather than hope the model complied.
"""

from app.ai.contracts import ExerciseGeneratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Exercise
from app.domain.enums import ExerciseType
from app.domain.ports import ClockPort, ExerciseRepository, GoalRepository, IdGeneratorPort
from app.services.context_builder import ContextBuilder, GoalNotFoundError

TEACH_BACK_PROMPT_VERSION = "exercise_generator.v1"

TEACH_BACK_INSTRUCTION = (
    "Generate a teach-back prompt: ask the learner to explain this "
    "concept in their own words, as if teaching it to someone who has "
    "never seen it before. Do not ask them to solve a problem -- ask "
    "them to explain the idea, why it matters, and how it works."
)


class TeachBackService:
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

    async def generate_teach_back(self, goal_id: str, concept_id: str) -> Exercise:
        goal = self._goals.get(goal_id)
        if goal is None:
            raise GoalNotFoundError(goal_id)

        request = AIRequest(
            role="exercise_generator",
            prompt_version=TEACH_BACK_PROMPT_VERSION,
            goal={"id": goal.id, "title": goal.title, "target_level": goal.target_level.value},
            context=self._context_builder.build(goal_id, concept_id),
            task={
                "concept_id": concept_id,
                "exercise_type": "teach_back",
                "instruction": TEACH_BACK_INSTRUCTION,
            },
        )
        response = await self._orchestrator.generate(request, ExerciseGeneratorResponse)
        assert isinstance(response, ExerciseGeneratorResponse)

        exercise = Exercise(
            id=self._ids.new_id("exercise"),
            type=ExerciseType.TEACH_BACK,
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
