from typing import Any

import yaml
from pydantic import BaseModel


class ParsedFrontmatter(BaseModel):
    """Result of parsing a note's YAML frontmatter.

    Never raises: a malformed block is reported via `error` with `body` set
    to the original content, so one bad file never aborts a whole scan --
    see docs/DATABASE_SCHEMA.md and the T039 acceptance criteria.
    """

    frontmatter: dict[str, Any]
    body: str
    error: str | None = None


def parse_frontmatter(content: str) -> ParsedFrontmatter:
    lines = content.split("\n")

    if not lines or lines[0].strip() != "---":
        return ParsedFrontmatter(frontmatter={}, body=content)

    closing_index: int | None = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = i
            break

    if closing_index is None:
        return ParsedFrontmatter(frontmatter={}, body=content, error="Frontmatter not closed")

    yaml_text = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :])

    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        return ParsedFrontmatter(frontmatter={}, body=content, error=str(exc))

    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        return ParsedFrontmatter(
            frontmatter={}, body=content, error="Frontmatter is not a YAML mapping"
        )

    return ParsedFrontmatter(frontmatter=parsed, body=body)
