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

`target_path` for a concept with no `obsidian_path` yet lands under
`03_Knowledge/Concepts/` using the concept's title, not its id
(docs/TASKS.md T139 fix) -- matches docs/OBSIDIAN_SCHEMA.md #2's default
vault structure and #15's own naming example ("Concept Title.md")
exactly; the previous `f"{concept.id}.md"` fallback (flat at vault
root, e.g. `concept_sql_window_functions.md`) matched neither and had
never been exercised outside tests, since nothing invoked this service
in production until T139 wired it to actually fire.
"""

import re

from app.ai.contracts import CuratorOperation, CuratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.ports import ConceptRepository, EvidenceRepository, GoalRepository
from app.obsidian.vault_resolver import VaultPathTraversalError, VaultResolver
from app.services.context_builder import ConceptNotFoundError, GoalNotFoundError

CURATOR_PROMPT_VERSION = "curator.v1"
MAX_RECENT_EVIDENCE = 5
DEFAULT_CONCEPT_NOTES_DIR = "03_Knowledge/Concepts"
_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def sanitize_concept_filename(title: str) -> str:
    """Strips characters invalid in a filename on Windows/macOS/Linux,
    keeping spaces/casing -- docs/OBSIDIAN_SCHEMA.md #15's own example
    is a literal, human-readable "Concept Title.md", not a slug. Public
    (not `_`-prefixed): `ProposalValidator` needs the exact same
    convention to accept the paths this service proposes."""
    cleaned = _INVALID_FILENAME_CHARS.sub("", " ".join(title.split())).strip()
    return cleaned or "Untitled concept"


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

        target_path = concept.obsidian_path or (
            f"{DEFAULT_CONCEPT_NOTES_DIR}/{sanitize_concept_filename(concept.title)}.md"
        )
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
