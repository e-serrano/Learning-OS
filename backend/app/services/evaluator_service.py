"""Evaluator -- grades an ExerciseAttempt against its Exercise
(docs/TASKS.md T073, docs/AI_CONTRACTS.md #8: correctness, reasoning,
completeness, independence, transfer).

AI evaluations are evidence, not absolute truth (docs/DOMAIN_MODEL.md
#9) -- this service stores the AI's judgment as an immutable Evaluation
record. Converting a valid evaluation into Evidence that actually
affects mastery is T074's job, not this one's.
"""

from app.ai.contracts import EvaluatorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Evaluation
from app.domain.ports import (
    ClockPort,
    EvaluationRepository,
    ExerciseAttemptRepository,
    ExerciseRepository,
    IdGeneratorPort,
)
from app.services.answer_submission_service import ExerciseNotFoundError

EVALUATOR_PROMPT_VERSION = "evaluator.v1"


class AttemptNotFoundError(Exception):
    pass


class EvaluatorService:
    def __init__(
        self,
        attempts: ExerciseAttemptRepository,
        exercises: ExerciseRepository,
        evaluations: EvaluationRepository,
        orchestrator: AIOrchestrator,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._attempts = attempts
        self._exercises = exercises
        self._evaluations = evaluations
        self._orchestrator = orchestrator
        self._clock = clock
        self._ids = ids

    async def evaluate(self, attempt_id: str) -> Evaluation:
        attempt = self._attempts.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(attempt_id)
        exercise = self._exercises.get(attempt.exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError(attempt.exercise_id)

        request = AIRequest(
            role="evaluator",
            prompt_version=EVALUATOR_PROMPT_VERSION,
            task={
                "prompt": exercise.prompt,
                "solution": exercise.solution,
                "success_criteria": exercise.success_criteria,
                "answer": attempt.answer,
                "confidence": attempt.confidence,
            },
        )
        response = await self._orchestrator.generate(request, EvaluatorResponse)
        assert isinstance(response, EvaluatorResponse)

        evaluation = Evaluation(
            id=self._ids.new_id("evaluation"),
            attempt_id=attempt_id,
            correctness=response.correctness,
            reasoning=response.reasoning,
            completeness=response.completeness,
            independence=response.independence,
            transfer=response.transfer,
            misconceptions=response.misconceptions,
            feedback=response.feedback,
            recommended_action=response.recommended_action,
            provider=self._orchestrator.provider_name,
            model=self._orchestrator.model,
            prompt_version=EVALUATOR_PROMPT_VERSION,
            created_at=self._clock.now(),
        )
        self._evaluations.add(evaluation)
        return evaluation
