from app.obsidian.diff_engine import generate_diff


def test_identical_content_has_no_changes() -> None:
    result = generate_diff("same\ntext\n", "same\ntext\n")
    assert result.has_changes is False
    assert result.unified == ""
    assert all(line.op == "equal" for line in result.lines)


def test_detects_added_line() -> None:
    result = generate_diff("line1\n", "line1\nline2\n")
    assert result.has_changes is True
    ops = [(line.op, line.text) for line in result.lines]
    assert ("added", "line2") in ops


def test_detects_removed_line() -> None:
    result = generate_diff("line1\nline2\n", "line1\n")
    ops = [(line.op, line.text) for line in result.lines]
    assert ("removed", "line2") in ops


def test_detects_changed_line_as_remove_plus_add() -> None:
    result = generate_diff("mastery: 2.0\n", "mastery: 3.5\n")
    ops = {(line.op, line.text) for line in result.lines}
    assert ("removed", "mastery: 2.0") in ops
    assert ("added", "mastery: 3.5") in ops


def test_unified_diff_contains_path_and_markers() -> None:
    result = generate_diff("old\n", "new\n", path="Concepts/note.md")
    assert "Concepts/note.md (before)" in result.unified
    assert "Concepts/note.md (after)" in result.unified
    assert "-old" in result.unified
    assert "+new" in result.unified


def test_empty_before_is_all_additions() -> None:
    result = generate_diff("", "line1\nline2")
    assert result.has_changes is True
    assert all(line.op == "added" for line in result.lines)


def test_empty_after_is_all_removals() -> None:
    result = generate_diff("line1\nline2", "")
    assert result.has_changes is True
    assert all(line.op == "removed" for line in result.lines)


def test_both_empty_has_no_changes() -> None:
    result = generate_diff("", "")
    assert result.has_changes is False
    assert result.lines == []


def test_equal_lines_preserved_around_a_change() -> None:
    before = "header\nold line\nfooter\n"
    after = "header\nnew line\nfooter\n"
    result = generate_diff(before, after)
    ops = [line.op for line in result.lines]
    assert "equal" in ops
    assert ops.count("equal") == 2
