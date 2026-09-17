from datetime import UTC, datetime

import pytest

from app.domain.enums import ProposalOperation
from app.obsidian.change_proposal import ChangeProposal, ProposalStatus
from app.services.write_verification import WriteVerificationError, verify_write

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _proposal(**overrides: object) -> ChangeProposal:
    defaults: dict[str, object] = dict(
        id="proposal_1",
        path="concept_1.md",
        operation=ProposalOperation.CREATE_FILE,
        section=None,
        content="# Concept 1\n",
        status=ProposalStatus.APPROVED,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return ChangeProposal(**defaults)  # type: ignore[arg-type]


def test_create_file_passes_when_written_content_matches() -> None:
    proposal = _proposal(content="# Concept 1\n")

    verify_write(proposal, "# Concept 1\n")


def test_create_file_fails_when_written_content_differs() -> None:
    proposal = _proposal(content="# Concept 1\n")

    with pytest.raises(WriteVerificationError, match="does not match"):
        verify_write(proposal, "# Something else\n")


def test_replace_managed_section_passes_when_section_matches() -> None:
    proposal = _proposal(
        operation=ProposalOperation.REPLACE_MANAGED_SECTION,
        section="SUMMARY",
        content="New summary.",
    )
    written = "<!-- LEARNING_OS:BEGIN:SUMMARY -->\nNew summary.\n<!-- LEARNING_OS:END:SUMMARY -->\n"

    verify_write(proposal, written)


def test_replace_managed_section_fails_when_section_body_differs() -> None:
    proposal = _proposal(
        operation=ProposalOperation.REPLACE_MANAGED_SECTION,
        section="SUMMARY",
        content="New summary.",
    )
    written = "<!-- LEARNING_OS:BEGIN:SUMMARY -->\nWrong body.\n<!-- LEARNING_OS:END:SUMMARY -->\n"

    with pytest.raises(WriteVerificationError, match="does not match"):
        verify_write(proposal, written)


def test_replace_managed_section_fails_when_section_missing_from_written_content() -> None:
    proposal = _proposal(
        operation=ProposalOperation.REPLACE_MANAGED_SECTION,
        section="SUMMARY",
        content="New summary.",
    )

    with pytest.raises(WriteVerificationError, match="does not match"):
        verify_write(proposal, "# Just a heading, no managed section\n")


def test_update_frontmatter_passes_when_it_parses() -> None:
    proposal = _proposal(
        operation=ProposalOperation.UPDATE_FRONTMATTER, content="status: usable\nmastery: 3.5"
    )
    written = "---\nstatus: usable\nmastery: 3.5\n---\n# Body\n"

    verify_write(proposal, written)


def test_update_frontmatter_fails_when_yaml_is_malformed() -> None:
    proposal = _proposal(
        operation=ProposalOperation.UPDATE_FRONTMATTER, content="status: [unterminated"
    )
    written = "---\nstatus: [unterminated\n---\n# Body\n"

    with pytest.raises(WriteVerificationError, match="failed to parse"):
        verify_write(proposal, written)


def test_add_link_passes_when_content_is_present() -> None:
    proposal = _proposal(operation=ProposalOperation.ADD_LINK, content="[[Related Concept]]")

    verify_write(proposal, "# Notes\nSome text.\n[[Related Concept]]\n")


def test_add_link_fails_when_content_is_missing() -> None:
    proposal = _proposal(operation=ProposalOperation.ADD_LINK, content="[[Related Concept]]")

    with pytest.raises(WriteVerificationError, match="missing after write"):
        verify_write(proposal, "# Notes\nSome text.\n")
