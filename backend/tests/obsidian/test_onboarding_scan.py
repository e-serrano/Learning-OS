from pathlib import Path

from app.obsidian.onboarding_scan import scan_vault_readonly


def test_missing_path_reports_not_exists(tmp_path: Path) -> None:
    result = scan_vault_readonly(str(tmp_path / "does-not-exist"))
    assert result.exists is False
    assert result.readable is False
    assert result.errors == ["Path does not exist"]


def test_file_instead_of_directory_reports_not_readable(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-dir.txt"
    file_path.write_text("hello")

    result = scan_vault_readonly(str(file_path))

    assert result.exists is True
    assert result.readable is False
    assert result.errors == ["Path is not a directory"]


def test_empty_vault_scans_to_zero_files(tmp_path: Path) -> None:
    result = scan_vault_readonly(str(tmp_path))
    assert result.exists is True
    assert result.readable is True
    assert result.markdown_file_count == 0
    assert result.errors == []


def test_counts_markdown_files_recursively(tmp_path: Path) -> None:
    (tmp_path / "note1.md").write_text("# One")
    nested = tmp_path / "Concepts"
    nested.mkdir()
    (nested / "note2.md").write_text("# Two")
    (tmp_path / "not-markdown.txt").write_text("ignore me")

    result = scan_vault_readonly(str(tmp_path))

    assert result.markdown_file_count == 2
    assert result.errors == []


def test_ignores_obsidian_directory(tmp_path: Path) -> None:
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()
    (obsidian_dir / "workspace.md").write_text("should not count")
    (tmp_path / "real-note.md").write_text("# Real")

    result = scan_vault_readonly(str(tmp_path))

    assert result.markdown_file_count == 1


def test_scan_never_writes_anything(tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text("# Note")
    before = {p.name: p.stat().st_mtime for p in tmp_path.rglob("*")}

    scan_vault_readonly(str(tmp_path))

    after = {p.name: p.stat().st_mtime for p in tmp_path.rglob("*")}
    assert before == after
    assert list(tmp_path.iterdir()) == [tmp_path / "note.md"]
