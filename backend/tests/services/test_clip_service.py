from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from app.domain.enums import ProposalOperation
from app.obsidian.change_proposal import ProposalStatus
from app.obsidian.vault_resolver import VaultResolver
from app.services.clip_service import MAX_SELECTION_LENGTH, ClipService, InvalidClipError

NOW = datetime(2026, 3, 4, 12, 30, 45, tzinfo=UTC)


class FakeProposalRepository:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, proposal: object) -> None:
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


@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


def _service(vault_dir: Path) -> tuple[ClipService, FakeProposalRepository]:
    proposals = FakeProposalRepository()
    service = ClipService(
        proposals,  # type: ignore[arg-type]
        VaultResolver(str(vault_dir)),
        FakeClock(),
        FakeIdGenerator(),
    )
    return service, proposals


def test_create_clip_persists_a_pending_create_file_proposal(vault_dir: Path) -> None:
    service, proposals = _service(vault_dir)

    proposal = service.create_clip(
        "https://example.com/window-functions",
        "Window Functions Explained",
        "A window function computes a value across a set of rows.",
    )

    assert proposal.operation == ProposalOperation.CREATE_FILE
    assert proposal.status == ProposalStatus.PENDING
    assert proposal.path.startswith("Clippings/")
    assert proposal.path.endswith(".md")
    assert proposals.added == [proposal]


def test_create_clip_path_includes_a_slug_of_the_title(vault_dir: Path) -> None:
    service, _ = _service(vault_dir)

    proposal = service.create_clip("https://example.com", "Window Functions Explained!", "text")

    assert "window-functions-explained" in proposal.path


def test_create_clip_falls_back_to_a_generic_slug_for_an_empty_title(vault_dir: Path) -> None:
    service, _ = _service(vault_dir)

    proposal = service.create_clip("https://example.com", "   ", "text")

    assert proposal.path == "Clippings/20260304123045-clip.md"


def test_create_clip_content_has_safe_yaml_frontmatter_and_the_selection(vault_dir: Path) -> None:
    service, _ = _service(vault_dir)

    proposal = service.create_clip(
        'https://example.com/a?b=c&d="quoted"',
        "A: Title, with colons",
        "The selected passage.",
    )

    assert proposal.content.startswith("---\n")
    frontmatter_end = proposal.content.index("---\n", 4)
    frontmatter_text = proposal.content[4:frontmatter_end]
    frontmatter = yaml.safe_load(frontmatter_text)
    assert frontmatter["source"] == 'https://example.com/a?b=c&d="quoted"'
    assert frontmatter["title"] == "A: Title, with colons"
    assert "The selected passage." in proposal.content


def test_create_clip_collapses_multiline_titles_to_one_line(vault_dir: Path) -> None:
    service, _ = _service(vault_dir)

    proposal = service.create_clip("https://example.com", "Line one\nLine two", "text")

    assert "\n" not in proposal.content.split("# ", 1)[1].split("\n", 1)[0]
    assert "Line one Line two" in proposal.content


def test_create_clip_rejects_a_blank_selection(vault_dir: Path) -> None:
    service, proposals = _service(vault_dir)

    with pytest.raises(InvalidClipError):
        service.create_clip("https://example.com", "Title", "   ")

    assert proposals.added == []


def test_create_clip_rejects_a_selection_over_the_length_limit(vault_dir: Path) -> None:
    service, proposals = _service(vault_dir)

    with pytest.raises(InvalidClipError):
        service.create_clip("https://example.com", "Title", "x" * (MAX_SELECTION_LENGTH + 1))

    assert proposals.added == []
