from pathlib import Path

FORBIDDEN_SUBSTRINGS = (
    "import fastapi",
    "from fastapi",
    "import sqlalchemy",
    "from sqlalchemy",
    "import react",
    "from starlette",
    "import starlette",
)

DOMAIN_DIR = Path(__file__).resolve().parents[2] / "app" / "domain"


def _domain_source_files() -> list[Path]:
    return list(DOMAIN_DIR.rglob("*.py"))


def test_domain_package_has_source_files() -> None:
    assert len(_domain_source_files()) > 0


def test_domain_code_never_imports_forbidden_frameworks() -> None:
    """docs/AGENTS.md #4: domain code must not import FastAPI/React/SQLAlchemy/etc."""
    violations = []
    for path in _domain_source_files():
        text = path.read_text(encoding="utf-8").lower()
        for needle in FORBIDDEN_SUBSTRINGS:
            if needle in text:
                violations.append(f"{path}: contains {needle!r}")

    assert violations == []
