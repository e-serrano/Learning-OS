from pathlib import Path

from app.obsidian.markdown_scanner import scan_markdown_files
from app.obsidian.vault_resolver import VaultResolver


def _touch(path: Path, content: str = "# Note") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_empty_vault_returns_no_files(tmp_path: Path) -> None:
    resolver = VaultResolver(str(tmp_path))
    result = scan_markdown_files(resolver)
    assert result.files == []
    assert result.errors == []


def test_finds_markdown_files_recursively(tmp_path: Path) -> None:
    _touch(tmp_path / "note1.md")
    _touch(tmp_path / "03_Knowledge" / "Concepts" / "note2.md")
    _touch(tmp_path / "not-markdown.txt")

    resolver = VaultResolver(str(tmp_path))
    result = scan_markdown_files(resolver)

    paths = {f.path for f in result.files}
    assert paths == {"note1.md", "03_Knowledge/Concepts/note2.md"}


def test_ignores_obsidian_directory(tmp_path: Path) -> None:
    _touch(tmp_path / ".obsidian" / "workspace.md")
    _touch(tmp_path / "real-note.md")

    resolver = VaultResolver(str(tmp_path))
    result = scan_markdown_files(resolver)

    assert {f.path for f in result.files} == {"real-note.md"}


def test_ignores_default_attachments_and_templates_dirs(tmp_path: Path) -> None:
    _touch(tmp_path / "Attachments" / "scan.md")
    _touch(tmp_path / "Templates" / "template.md")
    _touch(tmp_path / "keep.md")

    resolver = VaultResolver(str(tmp_path))
    result = scan_markdown_files(resolver)

    assert {f.path for f in result.files} == {"keep.md"}


def test_custom_ignored_dirs_overrides_default(tmp_path: Path) -> None:
    _touch(tmp_path / "Attachments" / "scan.md")

    resolver = VaultResolver(str(tmp_path))
    result = scan_markdown_files(resolver, ignored_dirs=frozenset({".obsidian"}))

    assert {f.path for f in result.files} == {"Attachments/scan.md"}


def test_paths_are_posix_style_and_relative(tmp_path: Path) -> None:
    _touch(tmp_path / "03_Knowledge" / "Concepts" / "note.md")

    resolver = VaultResolver(str(tmp_path))
    result = scan_markdown_files(resolver)

    assert result.files[0].path == "03_Knowledge/Concepts/note.md"
    assert "\\" not in result.files[0].path


def test_scan_never_writes_anything(tmp_path: Path) -> None:
    _touch(tmp_path / "note.md")
    before = sorted(p.name for p in tmp_path.rglob("*"))

    resolver = VaultResolver(str(tmp_path))
    scan_markdown_files(resolver)

    after = sorted(p.name for p in tmp_path.rglob("*"))
    assert before == after
