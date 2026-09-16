"""Diagnostic service -- proposes diagnostic items spanning recall,
application, and transfer (docs/AI_CONTRACTS.md #5), and turns an
already-graded response into Evidence (docs/TASKS.md T066).

AI only proposes questions; it never grades itself or assigns evidence
scores directly (docs/AGENTS.md #5: AI output never directly mutates
application state) -- `record_response` requires the caller to supply
`correctness` already graded (by the Evaluator AI role or otherwise).
"""

from typing import Any, Literal

from app.ai.contracts import DiagnosticianResponse, DiagnosticItem
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.entities import Evidence
from app.domain.enums import EvidenceSourceType
from app.domain.ports import ClockPort, EvidenceRepository, GoalRepository, IdGeneratorPort
from app.services.context_builder import ContextBuilder, GoalNotFoundError

DIAGNOSTICIAN_PROMPT_VERSION = "diagnostician.v1"


class DiagnosticService:
    def __init__(
        self,
        goals: GoalRepository,
        evidence: EvidenceRepository,
        context_builder: ContextBuilder,
        orchestrator: AIOrchestrator,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._goals = goals
        self._evidence = evidence
        self._context_builder = context_builder
        self._orchestrator = orchestrator
        self._clock = clock
        self._ids = ids

    async def generate_items(self, goal_id: str, concept_ids: list[str]) -> list[DiagnosticItem]:
        """Samples prerequisite concepts before advanced ones is the AI's
        job (docs/AI_CONTRACTS.md #5 instructions) -- this method just
        assembles the context and forwards the request."""
        goal = self._goals.get(goal_id)
        if goal is None:
            raise GoalNotFoundError(goal_id)

        request = AIRequest(
            role="diagnostician",
            prompt_version=DIAGNOSTICIAN_PROMPT_VERSION,
            goal={"id": goal.id, "title": goal.title, "target_level": goal.target_level.value},
            context=self._merged_context(goal_id, concept_ids),
            task={"concept_ids": concept_ids},
        )
        response = await self._orchestrator.generate(request, DiagnosticianResponse)
        assert isinstance(response, DiagnosticianResponse)
        return response.items

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

    def record_response(
        self,
        goal_id: str,
        concept_id: str,
        activity_id: str,
        evidence_type: Literal["recall", "application", "transfer"],
        correctness: float,
        difficulty: int,
        session_id: str | None = None,
        question: str | None = None,
    ) -> Evidence:
        """Turns one graded diagnostic response into Evidence
        (`source_type=assessment`). `evidence_type` additionally sets the
        matching Evidence dimension -- `application` also populates
        `reasoning` (applying knowledge is a reasoning task), `transfer`
        also populates `transfer` -- so downstream signals (mastery,
        activity selection) that key on those specific fields see
        diagnostic-sourced data, not just recall."""
        reasoning = correctness if evidence_type == "application" else None
        transfer = correctness if evidence_type == "transfer" else None

        metadata: dict[str, Any] = {
            "assessment_type": "diagnostic",
            "evidence_type": evidence_type,
        }
        if question is not None:
            metadata["question"] = question

        evidence = Evidence(
            id=self._ids.new_id("evidence"),
            concept_id=concept_id,
            goal_id=goal_id,
            activity_id=activity_id,
            session_id=session_id,
            source_type=EvidenceSourceType.ASSESSMENT,
            difficulty=difficulty,
            correctness=correctness,
            reasoning=reasoning,
            transfer=transfer,
            timestamp=self._clock.now(),
            metadata=metadata,
        )
        self._evidence.add(evidence)
        return evidence
