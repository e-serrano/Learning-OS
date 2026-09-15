def _markers(name: str) -> tuple[str, str]:
    return f"<!-- LEARNING_OS:BEGIN:{name} -->", f"<!-- LEARNING_OS:END:{name} -->"


class ManagedSectionError(ValueError):
    """A BEGIN marker exists with no matching END marker."""


def get_section(content: str, name: str) -> str | None:
    """Return the body of managed section `name`, or None if absent.

    See docs/OBSIDIAN_SCHEMA.md #5. User content outside managed sections
    is never touched by these functions.
    """
    begin_marker, end_marker = _markers(name)
    begin_idx = content.find(begin_marker)
    if begin_idx == -1:
        return None

    content_start = begin_idx + len(begin_marker)
    end_idx = content.find(end_marker, content_start)
    if end_idx == -1:
        return None

    raw = content[content_start:end_idx]
    if raw.startswith("\n"):
        raw = raw[1:]
    if raw.endswith("\n"):
        raw = raw[:-1]
    return raw


def replace_section(content: str, name: str, new_body: str) -> str:
    """Replace managed section `name`'s body, or append the section if absent.

    Raises ManagedSectionError if a BEGIN marker exists with no matching
    END marker, rather than guessing and risking corrupting the file.
    """
    begin_marker, end_marker = _markers(name)
    begin_idx = content.find(begin_marker)

    if begin_idx == -1:
        separator = "" if content == "" or content.endswith("\n") else "\n"
        return f"{content}{separator}{begin_marker}\n{new_body}\n{end_marker}\n"

    content_start = begin_idx + len(begin_marker)
    end_idx = content.find(end_marker, content_start)
    if end_idx == -1:
        raise ManagedSectionError(f"Managed section {name!r} has BEGIN marker but no END marker")

    return f"{content[:content_start]}\n{new_body}\n{content[end_idx:]}"
