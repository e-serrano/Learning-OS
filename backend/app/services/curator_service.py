"""Curator -- proposes knowledge updates for a concept's vault note from
recent evidence (docs/TASKS.md T080, docs/AI_CONTRACTS.md #9: input is
proposed changes, target note, current note, evidence, session outcome).

Unlike every other AI role built so far, the curator's input includes
real vault content ("current note") -- reading it here, through
VaultResolver (read-only), is the one place in this pipeline that
touches the filesystem directly.

Returns the AI's raw proposed operations, unvalidated and unpersisted.
Turning a validated operation into a persisted ChangeProposal is T081's
job: "the application validates every operation" before it ever becomes
one (docs/AI_CONTRACTS.md #9, and CuratorResponse's own docstring).
"""

from app.ai.contracts import CuratorOperation, CuratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.ports import ConceptRepository, EvidenceRepository, GoalRepository
from app.obsidian.vault_resolver import VaultPathTraversalError, VaultResolver
from app.services.context_builder import ConceptNotFoundError, GoalNotFoundError

CURATOR_PROMPT_VERSION = "curator.v1"
MAX_RECENT_EVIDENCE = 5


class CuratorService:
    def __init__(
        self,
        goals: GoalRepository,
        concepts: ConceptRepository,
        evidence: EvidenceRepository,
        vault: VaultResolver,
        orchestrator: AIOrchestrator,
    ) -> None:
        self._goals = goals
        self._concepts = concepts
        self._evidence = evidence
        self._vault = vault
        self._orchestrator = orchestrator

    async def propose(
        self, goal_id: str, concept_id: str, session_outcome: str | None = None
    ) -> list[CuratorOperation]:
        goal = self._goals.get(goal_id)
        if goal is None:
            raise GoalNotFoundError(goal_id)
        concept = self._concepts.get(concept_id)
        if concept is None:
            raise ConceptNotFoundError(concept_id)

        target_path = concept.obsidian_path or f"{concept.id}.md"
        recent_evidence = sorted(
            self._evidence.list_by_concept(concept_id),
            key=lambda e: e.timestamp,
            reverse=True,
        )[:MAX_RECENT_EVIDENCE]

        request = AIRequest(
            role="curator",
            prompt_version=CURATOR_PROMPT_VERSION,
            goal={"id": goal.id, "title": goal.title},
            current_state={
                "target_note": target_path,
                "current_note": self._read_current_note(target_path),
                "concept": {
                    "id": concept.id,
                    "title": concept.title,
                    "mastery": concept.mastery,
                    "status": concept.status.value,
                },
            },
            context=[
                {
                    "kind": "evidence",
                    "source_type": e.source_type.value,
                    "correctness": e.correctness,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in recent_evidence
            ],
            task={"session_outcome": session_outcome or ""},
        )
        response = await self._orchestrator.generate(request, CuratorResponse)
        assert isinstance(response, CuratorResponse)
        return response.operations

    def _read_current_note(self, relative_path: str) -> str:
        try:
            path = self._vault.resolve(relative_path)
        except VaultPathTraversalError:
            return ""
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")
