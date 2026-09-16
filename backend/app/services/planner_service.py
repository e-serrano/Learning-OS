"""80/20 planner -- identifies high-leverage concepts, deferred topics,
and the diagnostic focus to test first for a goal (docs/TASKS.md T067,
docs/AI_CONTRACTS.md #4: "distinguish high-leverage fundamentals from
advanced optional knowledge").

`PlannerResponse` also carries `roadmap_nodes`/`roadmap_edges`, but
turning those into persisted concepts/relations is T068's job (Roadmap
service), which validates the graph -- IDs, self-relations, cycles --
before anything is written. This service only calls the AI and surfaces
its proposal; it never persists a roadmap or concepts itself
(docs/AGENTS.md #5: AI output never directly mutates application state
without going through validation).
"""

from dataclasses import dataclass

from app.ai.contracts import HighLeverageConcept, PlannerResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.ports import ConceptRepository, GoalRepository
from app.services.context_builder import GoalNotFoundError

PLANNER_PROMPT_VERSION = "planner.v1"


@dataclass(frozen=True)
class PlanningResult:
    high_leverage_concepts: list[HighLeverageConcept]
    deferred_topics: list[str]
    diagnostic_focus: list[str]


class PlannerService:
    def __init__(
        self,
        goals: GoalRepository,
        concepts: ConceptRepository,
        orchestrator: AIOrchestrator,
    ) -> None:
        self._goals = goals
        self._concepts = concepts
        self._orchestrator = orchestrator

    async def plan(self, goal_id: str) -> PlanningResult:
        """Input per docs/AI_CONTRACTS.md #4: goal, user level, existing
        knowledge, target outcome, available time. "Existing knowledge" is
        whatever concepts are already linked to the goal -- empty for a
        brand-new one, since concept creation itself is deferred to T068."""
        goal = self._goals.get(goal_id)
        if goal is None:
            raise GoalNotFoundError(goal_id)

        existing_knowledge = [
            {
                "concept_id": concept.id,
                "title": concept.title,
                "mastery": concept.mastery,
                "status": concept.status.value,
            }
            for concept in self._concepts.list_by_goal(goal_id)
        ]
        request = AIRequest(
            role="planner",
            prompt_version=PLANNER_PROMPT_VERSION,
            goal={
                "id": goal.id,
                "title": goal.title,
                "description": goal.description,
                "target_level": goal.target_level.value,
            },
            current_state={"existing_knowledge": existing_knowledge},
            task={"available_minutes_per_week": goal.available_minutes_per_week},
        )
        response = await self._orchestrator.generate(request, PlannerResponse)
        assert isinstance(response, PlannerResponse)
        return PlanningResult(
            high_leverage_concepts=response.high_leverage_concepts,
            deferred_topics=response.deferred_topics,
            diagnostic_focus=response.diagnostic_focus,
        )
