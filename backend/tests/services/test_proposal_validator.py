from datetime import UTC, datetime
from pathlib import Path

from app.ai.contracts import CuratorOperation
from app.domain.entities import Concept
from app.domain.enums import ConceptStatus, ProposalOperation
from app.obsidian.change_proposal import ChangeProposal, ProposalStatus
from app.obsidian.vault_resolver import VaultResolver
from app.services.proposal_validator import (
    MAX_CONTENT_LENGTH,
    MAX_OPERATIONS_PER_BATCH,
    ProposalValidator,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeChangeProposalRepository:
    def __init__(self) -> None:
        self.added: list[ChangeProposal] = []

    def add(self, proposal: ChangeProposal) -> None:
        self.added.append(proposal)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class FakeIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


def _concept(**overrides: object) -> Concept:
    defaults: dict[str, object] = dict(
        id="concept_1",
        title="Window Functions",
        domain="sql",
        status=ConceptStatus.LEARNING,
        mastery=2,
        confidence=40,
        importance=3,
        retention=30,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return Concept(**defaults)  # type: ignore[arg-type]


def _operation(**overrides: object) -> CuratorOperation:
    defaults: dict[str, object] = dict(
        path="concept_1.md",
        operation=ProposalOperation.REPLACE_MANAGED_SECTION,
        section="SUMMARY",
        content="Window functions compute values across row sets.",
    )
    defaults.update(overrides)
    return CuratorOperation(**defaults)  # type: ignore[arg-type]


def _validator(vault_root: Path) -> tuple[ProposalValidator, FakeChangeProposalRepository]:
    proposals = FakeChangeProposalRepository()
    validator = ProposalValidator(
        proposals, VaultResolver(str(vault_root)), FakeClock(), FakeIdGenerator()
    )
    return validator, proposals


def test_valid_operation_is_accepted_and_persisted(tmp_path: Path) -> None:
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    validator, proposals = _validator(vault_root)

    result = validator.validate_and_persist([_operation()], _concept())

    assert len(result.accepted) == 1
    assert result.rejected == []
    assert proposals.added == result.accepted
    assert result.accepted[0].status == ProposalStatus.PENDING


def test_create_file_for_a_concept_without_obsidian_path_uses_conventional_name(
    tmp_path: Path,
) -> None:
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    validator, _ = _validator(vault_root)
    op = _operation(
        path="concept_1.md",
        operation=ProposalOperation.CREATE_FILE,
        section=None,
        content="# New note",
    )

    result = validator.validate_and_persist([op], _concept(obsidian_path=None))

    assert len(result.accepted) == 1


def test_existing_obsidian_path_is_respected(tmp_path: Path) -> None:
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    validator, _ = _validator(vault_root)
    op = _operation(path="concepts/window_functions.md")

    result = validator.validate_and_persist(
        [op], _concept(obsidian_path="concepts/window_functions.md")
    )

    assert len(result.accepted) == 1


def test_replace_managed_section_without_section_is_rejected(tmp_path: Path) -> None:
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    validator, proposals = _validator(vault_root)
    op = _operation(section=None)

    result = validator.validate_and_persist([op], _concept())

    assert result.accepted == []
    assert len(result.rejected) == 1
    assert "section" in result.rejected[0].reason
    assert proposals.added == []


def test_non_markdown_path_is_rejected(tmp_path: Path) -> None:
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    validator, _ = _validator(vault_root)
    op = _operation(path="concept_1.txt")

    result = validator.validate_and_persist([op], _concept())

    assert result.accepted == []
    assert "markdown" in result.rejected[0].reason


def test_path_in_ignored_directory_is_rejected(tmp_path: Path) -> None:
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    validator, _ = _validator(vault_root)
    op = _operation(path="Templates/concept_1.md")

    result = validator.validate_and_persist([op], _concept(obsidian_path="Templates/concept_1.md"))

    assert result.accepted == []
    assert "ignored directory" in result.rejected[0].reason


def test_path_traversal_is_rejected(tmp_path: Path) -> None:
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    validator, _ = _validator(vault_root)
    op = _operation(path="../../etc/passwd.md")

    result = validator.validate_and_persist([op], _concept(obsidian_path="../../etc/passwd.md"))

    assert result.accepted == []
    assert "escapes" in result.rejected[0].reason


def test_path_not_belonging_to_the_curated_concept_is_rejected(tmp_path: Path) -> None:
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    validator, _ = _validator(vault_root)
    op = _operation(path="some_other_concept.md")

    result = validator.validate_and_persist([op], _concept(obsidian_path=None))

    assert result.accepted == []
    assert "does not belong" in result.rejected[0].reason


def test_content_over_the_length_limit_is_rejected(tmp_path: Path) -> None:
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    validator, _ = _validator(vault_root)
    op = _operation(content="x" * (MAX_CONTENT_LENGTH + 1))

    result = validator.validate_and_persist([op], _concept())

    assert result.accepted == []
    assert "exceeds" in result.rejected[0].reason


def test_batch_size_over_the_limit_rejects_the_overflow(tmp_path: Path) -> None:
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    validator, _ = _validator(vault_root)
    operations = [_operation() for _ in range(MAX_OPERATIONS_PER_BATCH + 3)]

    result = validator.validate_and_persist(operations, _concept())

    assert len(result.accepted) == MAX_OPERATIONS_PER_BATCH
    assert len(result.rejected) == 3
    assert all("batch size" in r.reason for r in result.rejected)
