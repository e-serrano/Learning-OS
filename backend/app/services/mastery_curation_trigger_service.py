"""Mastery curation trigger -- proposes a concept's vault note be
created/updated the moment its status crosses into MASTERED (docs/TASKS.md
T139, user request).

`CuratorService` (T080) and `ProposalValidator` (T081) were built
complete but never invoked from any application flow -- T121's own DONE
note flagged this explicitly as "a real gap... documented here for
whoever decides where curator should fire in production." This is that
decision: the moment `MasteryEngine` (T061) derives
`ConceptStatus.MASTERED` for a concept, a curator proposal is generated
automatically -- never auto-applied, still a normal pending
`ChangeProposal` a human reviews via the Vault diff UI/Obsidian plugin/
browser extension (whichever review surface they use), same "AI
proposes, the user approves" principle every other proposal source
already follows (docs/AGENTS.md #5/#9).

Best-effort by construction: nothing here may ever break the evidence/
mastery-recording transaction that triggered it. Vault-not-configured or
AI-provider-not-configured is handled entirely by the caller
(`app/api/dependencies.py`'s `_build_curation_trigger`, which wires this
service in as `None` when either is unavailable, rather than this class
having to know about that); a failure *during* the AI call itself
(`AIInvalidOutputError`/`AIProviderUnavailableError`) is swallowed here.

Only fires on a genuine transition (`previous_status != MASTERED`), not
on every subsequent evidence event for an already-mastered concept --
otherwise every later successful review/exercise for a long-mastered
concept would re-trigger a real AI call for no new information. It DOES
re-fire if a concept ever drops out of MASTERED and re-enters it later --
a second synthesis point is genuinely new information, matching the
request that the vault note keep growing as understanding develops,
not stay a one-shot snapshot.
"""

from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.domain.entities import Concept
from app.domain.enums import ConceptStatus
from app.obsidian.change_proposal import ChangeProposal
from app.services.curator_service import CuratorService
from app.services.proposal_validator import ProposalValidator


class MasteryCurationTriggerService:
    def __init__(self, curator: CuratorService, proposal_validator: ProposalValidator) -> None:
        self._curator = curator
        self._proposal_validator = proposal_validator

    async def trigger_if_newly_mastered(
        self, goal_id: str, previous_status: ConceptStatus, updated: Concept
    ) -> ChangeProposal | None:
        if previous_status == ConceptStatus.MASTERED or updated.status != ConceptStatus.MASTERED:
            return None

        try:
            operations = await self._curator.propose(goal_id, updated.id)
        except (AIInvalidOutputError, AIProviderUnavailableError):
            return None

        result = self._proposal_validator.validate_and_persist(operations, updated)
        return result.accepted[0] if result.accepted else None
