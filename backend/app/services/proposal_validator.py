"""Proposal validator -- validates a curator's proposed operations
before any of them may become a persisted ChangeProposal (docs/TASKS.md
T081, docs/AI_CONTRACTS.md #9: "The application validates every
operation").

A malformed `operation` enum value never reaches here at all -- it would
already have failed schema validation (AIInvalidOutputError, T057's
retry/fallback) before the orchestrator ever returned a CuratorResponse.
What's left to check here are business rules the schema can't express:

- path: must resolve inside the vault (no traversal), must not target
  an ignored directory (`.obsidian/`, `Attachments/`, `Templates/` --
  same set the markdown scanner already ignores), must end in `.md`.
- concept ID: the path must actually belong to the concept this batch
  was curated for -- either its existing `obsidian_path`, or the
  conventional new-note name for that concept (matches CuratorService's
  own convention).
- section: required for `replace_managed_section` -- there is nothing
  to replace without naming a section.
- limits: content length and batch size are capped.

Operations that fail any check are dropped, not persisted -- a rejected
operation here is not the same thing as a user-rejected ChangeProposal
(`ProposalStatus.REJECTED` means a person saw and declined a valid
diff); these never became one.
"""

from dataclasses import dataclass, field

from app.ai.contracts import CuratorOperation
from app.domain.entities import Concept
from app.domain.enums import ProposalOperation
from app.domain.ports import ClockPort, IdGeneratorPort
from app.obsidian.change_proposal import ChangeProposal, ChangeProposalRepository, ProposalStatus
from app.obsidian.markdown_scanner import DEFAULT_IGNORED_DIRS
from app.obsidian.vault_resolver import VaultPathTraversalError, VaultResolver

MAX_CONTENT_LENGTH = 20_000
MAX_OPERATIONS_PER_BATCH = 20


@dataclass(frozen=True)
class RejectedOperation:
    operation: CuratorOperation
    reason: str


@dataclass(frozen=True)
class ValidationResult:
    accepted: list[ChangeProposal] = field(default_factory=list)
    rejected: list[RejectedOperation] = field(default_factory=list)


class ProposalValidator:
    def __init__(
        self,
        proposals: ChangeProposalRepository,
        vault: VaultResolver,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._proposals = proposals
        self._vault = vault
        self._clock = clock
        self._ids = ids

    def validate_and_persist(
        self, operations: list[CuratorOperation], concept: Concept
    ) -> ValidationResult:
        batch, overflow = (
            operations[:MAX_OPERATIONS_PER_BATCH],
            operations[MAX_OPERATIONS_PER_BATCH:],
        )

        accepted: list[ChangeProposal] = []
        rejected: list[RejectedOperation] = [
            RejectedOperation(op, "batch size limit exceeded") for op in overflow
        ]
        for operation in batch:
            reason = self._check(operation, concept)
            if reason is not None:
                rejected.append(RejectedOperation(operation, reason))
                continue
            accepted.append(self._persist(operation))

        return ValidationResult(accepted=accepted, rejected=rejected)

    def _check(self, operation: CuratorOperation, concept: Concept) -> str | None:
        if len(operation.content) > MAX_CONTENT_LENGTH:
            return f"content exceeds {MAX_CONTENT_LENGTH} characters"
        if (
            operation.operation == ProposalOperation.REPLACE_MANAGED_SECTION
            and not operation.section
        ):
            return "replace_managed_section requires a section"
        if not operation.path.endswith(".md"):
            return "path must be a markdown file"
        if any(operation.path.startswith(f"{d}/") for d in DEFAULT_IGNORED_DIRS):
            return "path targets an ignored directory"
        try:
            self._vault.resolve(operation.path)
        except VaultPathTraversalError:
            return "path escapes the vault root"
        if not self._path_belongs_to_concept(operation.path, concept):
            return "path does not belong to the curated concept"
        return None

    def _path_belongs_to_concept(self, path: str, concept: Concept) -> bool:
        if concept.obsidian_path is not None:
            return path == concept.obsidian_path
        return path == f"{concept.id}.md"

    def _persist(self, operation: CuratorOperation) -> ChangeProposal:
        now = self._clock.now()
        proposal = ChangeProposal(
            id=self._ids.new_id("proposal"),
            path=operation.path,
            operation=operation.operation,
            section=operation.section,
            content=operation.content,
            status=ProposalStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        self._proposals.add(proposal)
        return proposal
