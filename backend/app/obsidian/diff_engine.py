import difflib

from pydantic import BaseModel


class DiffLine(BaseModel):
    op: str
    """"equal" | "added" | "removed"."""
    text: str


class DiffResult(BaseModel):
    unified: str
    """Standard unified-diff text, for a simple text/code display."""
    lines: list[DiffLine]
    """Line-level breakdown, for a custom inline/side-by-side UI."""
    has_changes: bool


def generate_diff(before: str, after: str, path: str = "note.md") -> DiffResult:
    """Human-readable before/after diff -- see docs/API_SPEC.md #2 (vault changes)."""
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)

    unified = "".join(
        difflib.unified_diff(
            before_lines, after_lines, fromfile=f"{path} (before)", tofile=f"{path} (after)"
        )
    )

    lines: list[DiffLine] = []
    for entry in difflib.ndiff(before.splitlines(), after.splitlines()):
        prefix, text = entry[:2], entry[2:]
        if prefix == "  ":
            lines.append(DiffLine(op="equal", text=text))
        elif prefix == "+ ":
            lines.append(DiffLine(op="added", text=text))
        elif prefix == "- ":
            lines.append(DiffLine(op="removed", text=text))
        # "? " hint lines (character-level cues) are dropped; not needed for a line-level UI diff

    return DiffResult(unified=unified, lines=lines, has_changes=before != after)
