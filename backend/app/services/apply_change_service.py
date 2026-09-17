"""Apply approved change -- writes an approved ChangeProposal to the
vault (docs/TASKS.md T083). Only ever writes an `approved` proposal,
never a merely-pending one -- approval (T082) is the gate.

Computing the final file content differs per operation (the only 4
allowed types, docs/AGENTS.md #6):

- `create_file`: `proposal.content` is the whole new file. Refuses to
  overwrite an existing file -- "create" must never silently clobber.
- `replace_managed_section`: merges into the current file via
  `managed_sections.replace_section()`, which already handles a missing
  file/section by appending it (docs/OBSIDIAN_SCHEMA.md #5) -- so this
  also doubles as "create a note whose first content is this section."
- `update_frontmatter`: `proposal.content` is the full replacement YAML
  frontmatter block; the body below it is kept as-is (`parse_frontmatter`
  only parses -- a full round-trip-preserving frontmatter writer,
  keeping comments/formatting, is a larger and separate concern than
  "apply an approved change").
- `add_link`: `proposal.content` is appended as a new line at the end of
  the file. It is written exactly as the user already saw and approved
  in the diff -- no further interpretation here.

The write itself (conflict check, atomic replace, byte-level
reread-verify, index update) is entirely T044's `write_note()`; this
service only computes *what* to write and reacts to the outcome -- a
vault conflict marks the proposal `conflicted`. After a successful
write, T084's `verify_write()` does a second, semantic check (does the
written content actually parse back the way it should for this
operation type); either kind of verification failure marks the proposal
`failed`.

`compute_content()` is public and side-effect-free (only reads) so a
diff preview can show before/after content for a still-pending proposal
without writing anything -- see T085's knowledge E2E.
"""

from sqlalchemy import Engine

from app.domain.enums import ProposalOperation
from app.obsidian.atomic_writer import AtomicWriteVerificationError, write_note
from app.obsidian.change_proposal import ChangeProposal, ChangeProposalRepository, ProposalStatus
from app.obsidian.conflict_detection import VaultConflictError
from app.obsidian.frontmatter import parse_frontmatter
from app.obsidian.managed_sections import replace_section
from app.obsidian.vault_resolver import VaultResolver
from app.services.diff_approval_service import ProposalNotFoundError
from app.services.write_verification import WriteVerificationError, verify_write


class ProposalNotApprovedError(Exception):
    pass


class ApplyChangeError(Exception):
    """Content could not be computed; the caller marks the proposal failed."""


class ApplyChangeService:
    def __init__(
        self, engine: Engine, proposals: ChangeProposalRepository, vault: VaultResolver
    ) -> None:
        self._engine = engine
        self._proposals = proposals
        self._vault = vault

    def apply(self, proposal_id: str) -> ChangeProposal:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise ProposalNotFoundError(proposal_id)
        if proposal.status != ProposalStatus.APPROVED:
            raise ProposalNotApprovedError(
                f"proposal {proposal_id} is {proposal.status.value}, not approved"
            )

        try:
            new_content = self.compute_content(proposal)
        except ApplyChangeError as exc:
            self._proposals.update_status(proposal_id, ProposalStatus.FAILED, error=str(exc))
            return self._reload(proposal_id)

        try:
            write_note(self._engine, self._vault, proposal.path, new_content)
        except VaultConflictError as exc:
            self._proposals.update_status(proposal_id, ProposalStatus.CONFLICTED, error=str(exc))
            return self._reload(proposal_id)
        except AtomicWriteVerificationError as exc:
            self._proposals.update_status(proposal_id, ProposalStatus.FAILED, error=str(exc))
            return self._reload(proposal_id)

        try:
            verify_write(proposal, new_content)
        except WriteVerificationError as exc:
            self._proposals.update_status(proposal_id, ProposalStatus.FAILED, error=str(exc))
            return self._reload(proposal_id)

        self._proposals.update_status(proposal_id, ProposalStatus.APPLIED)
        return self._reload(proposal_id)

    def compute_content(self, proposal: ChangeProposal) -> str:
        """Public and side-effect-free (only reads the vault) so a diff
        preview (docs/API_SPEC.md #2: `GET /vault/changes`) can show
        before/after without writing anything -- see docs/TASKS.md T085."""
        current = self._read_current(proposal.path)

        if proposal.operation == ProposalOperation.CREATE_FILE:
            if current is not None:
                raise ApplyChangeError(f"{proposal.path} already exists, cannot create_file")
            return proposal.content

        if proposal.operation == ProposalOperation.REPLACE_MANAGED_SECTION:
            assert proposal.section is not None  # enforced by ProposalValidator, T081
            return replace_section(current or "", proposal.section, proposal.content)

        if proposal.operation == ProposalOperation.UPDATE_FRONTMATTER:
            body = parse_frontmatter(current or "").body
            return f"---\n{proposal.content}\n---\n{body}"

        if proposal.operation == ProposalOperation.ADD_LINK:
            base = current or ""
            separator = "" if base == "" or base.endswith("\n") else "\n"
            return f"{base}{separator}{proposal.content}\n"

        raise ApplyChangeError(f"unknown operation {proposal.operation!r}")

    def _read_current(self, path: str) -> str | None:
        target = self._vault.resolve(path)
        if not target.exists():
            return None
        return target.read_text(encoding="utf-8")

    def _reload(self, proposal_id: str) -> ChangeProposal:
        proposal = self._proposals.get(proposal_id)
        assert proposal is not None
        return proposal
