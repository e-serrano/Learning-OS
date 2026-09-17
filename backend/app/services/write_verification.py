"""Verify write -- semantic post-write check that a proposal's intended
change is actually retrievable through the application's own read-path
(docs/TASKS.md T084: "releer, verificar contenido y actualizar índice").

Rereading, byte-level content verification, and updating the vault
index are already entirely T044's `write_note()` job -- it guarantees
the file on disk is byte-for-byte the string T083 computed and passed
in. What that alone can't catch is a bug in *how* that string was
computed: this is a second, independent check that re-parses the same
written content through `get_section()`/`parse_frontmatter()`, the same
helpers the rest of the app uses to read a note back, per operation
type.
"""

from app.domain.enums import ProposalOperation
from app.obsidian.change_proposal import ChangeProposal
from app.obsidian.frontmatter import parse_frontmatter
from app.obsidian.managed_sections import get_section


class WriteVerificationError(Exception):
    pass


def verify_write(proposal: ChangeProposal, written_content: str) -> None:
    if proposal.operation == ProposalOperation.CREATE_FILE:
        if written_content != proposal.content:
            raise WriteVerificationError(
                f"{proposal.path}: written content does not match the proposal"
            )
        return

    if proposal.operation == ProposalOperation.REPLACE_MANAGED_SECTION:
        assert proposal.section is not None  # enforced by ProposalValidator, T081
        section_body = get_section(written_content, proposal.section)
        if section_body != proposal.content:
            raise WriteVerificationError(
                f"{proposal.path}: section {proposal.section!r} does not match after write"
            )
        return

    if proposal.operation == ProposalOperation.UPDATE_FRONTMATTER:
        parsed = parse_frontmatter(written_content)
        if parsed.error is not None:
            raise WriteVerificationError(
                f"{proposal.path}: frontmatter failed to parse after write ({parsed.error})"
            )
        return

    if proposal.operation == ProposalOperation.ADD_LINK:
        if proposal.content not in written_content:
            raise WriteVerificationError(f"{proposal.path}: link content missing after write")
        return

    raise WriteVerificationError(f"{proposal.path}: unknown operation {proposal.operation!r}")
