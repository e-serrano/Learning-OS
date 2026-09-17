"""Project evaluation -- grades a submitted deliverable for independence
and transfer (docs/TASKS.md T095).

A project has neither an Exercise nor an ExerciseAttempt
(docs/DOMAIN_MODEL.md #14; see T092's note), so `EvaluatorService`
(T073) can't be reused as-is -- it needs a real prompt/solution/
success_criteria tied to one exercise. This builds its own `AIRequest`
reusing the same `evaluator` role and `EvaluatorResponse` contract (same
reuse precedent as T089/T092), grading the deliverable against the
project's own objective/success_criteria.

Produces a second, *scored* Evidence row per concept -- T094's
submission evidence is unscored by design (see its note: it is inert
signal-wise until this step runs); this is the evidence that actually
carries a transfer/independence signal into
MasteryEngine/retention/activity-selection.
"""

from app.ai.contracts import EvaluatorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Evidence
from app.domain.enums import EvidenceSourceType
from app.domain.ports import ClockPort, EvidenceRepository, IdGeneratorPort, ProjectRepository
from app.services.project_submission_service import ProjectNotFoundError

EVALUATOR_PROMPT_VERSION = "evaluator.v1"


class ProjectEvaluationService:
    def __init__(
        self,
        projects: ProjectRepository,
        evidence: EvidenceRepository,
        orchestrator: AIOrchestrator,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._projects = projects
        self._evidence = evidence
        self._orchestrator = orchestrator
        self._clock = clock
        self._ids = ids

    async def evaluate_submission(
        self, project_id: str, task_id: str, session_id: str, deliverable: str
    ) -> list[Evidence]:
        project = self._projects.get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        request = AIRequest(
            role="evaluator",
            prompt_version=EVALUATOR_PROMPT_VERSION,
            task={
                "prompt": project.objective,
                "solution": "",
                "success_criteria": project.success_criteria,
                "answer": deliverable,
            },
        )
        response = await self._orchestrator.generate(request, EvaluatorResponse)
        assert isinstance(response, EvaluatorResponse)

        now = self._clock.now()
        created: list[Evidence] = []
        for concept_id in project.concept_ids:
            record = Evidence(
                id=self._ids.new_id("evidence"),
                concept_id=concept_id,
                goal_id=project.goal_id,
                session_id=session_id,
                activity_id=task_id,
                source_type=EvidenceSourceType.PROJECT,
                difficulty=project.difficulty,
                correctness=response.correctness,
                reasoning=response.reasoning,
                independence=response.independence,
                transfer=response.transfer,
                timestamp=now,
                metadata={
                    "feedback": response.feedback,
                    "misconceptions": response.misconceptions,
                },
            )
            self._evidence.add(record)
            created.append(record)

        return created
