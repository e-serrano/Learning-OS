import pytest

from app.obsidian.managed_sections import ManagedSectionError, get_section, replace_section

SAMPLE = """# SQL Window Functions

<!-- LEARNING_OS:BEGIN:SUMMARY -->
Generated summary.
<!-- LEARNING_OS:END:SUMMARY -->

## My understanding

User-written notes here, never touched.

<!-- LEARNING_OS:BEGIN:MASTERY -->
## Mastery

- Mastery: 3.2/5
<!-- LEARNING_OS:END:MASTERY -->
"""


def test_get_section_returns_body() -> None:
    assert get_section(SAMPLE, "SUMMARY") == "Generated summary."


def test_get_section_returns_none_when_absent() -> None:
    assert get_section(SAMPLE, "WEAKNESSES") is None


def test_get_section_with_multiline_body() -> None:
    result = get_section(SAMPLE, "MASTERY")
    assert result == "## Mastery\n\n- Mastery: 3.2/5"


def test_get_section_ignores_unrelated_name_with_shared_prefix() -> None:
    assert get_section(SAMPLE, "SUMMAR") is None


def test_replace_section_updates_existing_body_only() -> None:
    updated = replace_section(SAMPLE, "SUMMARY", "New summary text.")
    assert get_section(updated, "SUMMARY") == "New summary text."
    # untouched sections and user content survive
    assert "User-written notes here, never touched." in updated
    assert get_section(updated, "MASTERY") == "## Mastery\n\n- Mastery: 3.2/5"


def test_replace_section_appends_when_section_absent() -> None:
    content = "# Note\n\nSome user text.\n"
    updated = replace_section(content, "WEAKNESSES", "New weakness.")
    assert "Some user text." in updated
    assert get_section(updated, "WEAKNESSES") == "New weakness."


def test_replace_section_on_empty_content() -> None:
    updated = replace_section("", "SUMMARY", "Body.")
    assert get_section(updated, "SUMMARY") == "Body."


def test_replace_section_preserves_content_before_and_after() -> None:
    updated = replace_section(SAMPLE, "SUMMARY", "X")
    assert updated.startswith("# SQL Window Functions\n\n")
    assert updated.rstrip().endswith("<!-- LEARNING_OS:END:MASTERY -->")


def test_replace_section_raises_on_unclosed_marker() -> None:
    broken = "<!-- LEARNING_OS:BEGIN:SUMMARY -->\nno end marker"
    with pytest.raises(ManagedSectionError):
        replace_section(broken, "SUMMARY", "New body")


def test_roundtrip_replace_then_get_matches_exactly() -> None:
    body = "Line one.\nLine two.\nLine three."
    updated = replace_section(SAMPLE, "SUMMARY", body)
    assert get_section(updated, "SUMMARY") == body


def test_replace_is_idempotent_when_applied_twice_with_same_body() -> None:
    once = replace_section(SAMPLE, "SUMMARY", "Stable text.")
    twice = replace_section(once, "SUMMARY", "Stable text.")
    assert once == twice
