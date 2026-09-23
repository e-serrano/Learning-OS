"""Web clip ingestion -- turns a browser-extension-submitted page
selection into a pending `ChangeProposal` (docs/TASKS.md T135).

Every other `ChangeProposal` source (`ProposalValidator`, T081) is
driven by the Curator AI role and concept-scoped -- an operation must
name the concept it belongs to, validated against that concept's
`obsidian_path`. A clip has no concept association yet: it's raw,
unsorted source material captured while browsing, the same role
Obsidian's own web clipper plays (land in an inbox, distill into a real
note later). `CuratorOperation`'s concept-scoping validation doesn't
apply here for exactly that reason, so this is a parallel, smaller
creation path rather than a reuse of `ProposalValidator` -- every clip
lands under a fixed `Clippings/` prefix instead of a concept's own path.

Reuses the exact same review pipeline every other proposal already has
(`GET /vault/changes`, `POST /vault/changes/{id}/apply`/`reject`, T081/
T119's Vault diff UI) -- a clip is never written to the vault directly,
same "external input never mutates state, the app validates and the
user approves" principle (docs/AGENTS.md #5/#9) applied to browser input
instead of AI output.
"""

import re
from datetime import datetime

import yaml

from app.domain.enums import ProposalOperation
from app.domain.ports import ClockPort, IdGeneratorPort
from app.obsidian.change_proposal import ChangeProposal, ChangeProposalRepository, ProposalStatus
from app.obsidian.vault_resolver import VaultPathTraversalError, VaultResolver

CLIPPINGS_DIR = "Clippings"
MAX_SELECTION_LENGTH = 20_000
MAX_TITLE_LENGTH = 100


class InvalidClipError(ValueError):
    pass


class ClipService:
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

    def create_clip(self, url: str, title: str, selection: str) -> ChangeProposal:
        selection = selection.strip()
        if not selection:
            raise InvalidClipError("selection must not be blank")
        if len(selection) > MAX_SELECTION_LENGTH:
            raise InvalidClipError(f"selection exceeds {MAX_SELECTION_LENGTH} characters")

        now = self._clock.now()
        path = self._unique_path(title, now)
        try:
            self._vault.resolve(path)
        except VaultPathTraversalError as exc:
            raise InvalidClipError("generated path escapes the vault root") from exc

        proposal = ChangeProposal(
            id=self._ids.new_id("proposal"),
            path=path,
            operation=ProposalOperation.CREATE_FILE,
            content=self._render(url, title, selection, now),
            status=ProposalStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        self._proposals.add(proposal)
        return proposal

    def _unique_path(self, title: str, now: datetime) -> str:
        slug = _slugify(title) or "clip"
        timestamp = now.strftime("%Y%m%d%H%M%S")
        return f"{CLIPPINGS_DIR}/{timestamp}-{slug}.md"

    def _render(self, url: str, title: str, selection: str, now: datetime) -> str:
        safe_title = _single_line(title)[:MAX_TITLE_LENGTH] or "Untitled clip"
        frontmatter = yaml.safe_dump(
            {"source": url, "title": safe_title, "clipped_at": now.isoformat()},
            sort_keys=False,
        )
        return f"---\n{frontmatter}---\n\n# {safe_title}\n\n{selection}\n"


def _single_line(text: str) -> str:
    return " ".join(text.split())


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60]
