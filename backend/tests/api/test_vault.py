from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_apply_change_service,
    get_change_proposal_repository,
    get_config_store,
    get_diff_approval_service,
    get_vault_scan_service,
    get_vault_search_service,
)
from app.config.store import ConfigStore
from app.domain.enums import ProposalOperation
from app.main import app
from app.obsidian.change_proposal import ChangeProposal, ChangeProposalRepository, ProposalStatus
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.services.apply_change_service import ApplyChangeService
from app.services.diff_approval_service import DiffApprovalService
from app.services.vault_scan_service import VaultScanService
from app.services.vault_search_service import VaultSearchService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


@pytest.fixture
def engine(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def proposals(engine):  # type: ignore[no-untyped-def]
    return ChangeProposalRepository(engine)


@pytest.fixture
def client(
    tmp_path: Path, vault_dir: Path, engine, proposals: ChangeProposalRepository
) -> TestClient:
    Base.metadata.create_all(create_sqlite_engine(str(tmp_path / "config.sqlite3")))
    config_store = ConfigStore(str(tmp_path / "config.sqlite3"))
    config = config_store.load()
    config.vault_path = str(vault_dir)
    config_store.save(config)

    resolver = VaultResolver(str(vault_dir))
    app.dependency_overrides[get_config_store] = lambda: config_store
    app.dependency_overrides[get_change_proposal_repository] = lambda: proposals
    app.dependency_overrides[get_vault_scan_service] = lambda: VaultScanService(engine, resolver)
    app.dependency_overrides[get_apply_change_service] = lambda: ApplyChangeService(
        engine, proposals, resolver
    )
    app.dependency_overrides[get_diff_approval_service] = lambda: DiffApprovalService(proposals)
    app.dependency_overrides[get_vault_search_service] = lambda: VaultSearchService(engine)
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def _seed_proposal(proposals: ChangeProposalRepository, **overrides: object) -> ChangeProposal:
    defaults: dict[str, object] = dict(
        id="proposal_1",
        path="note.md",
        operation=ProposalOperation.CREATE_FILE,
        content="# New note\n",
        status=ProposalStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    proposal = ChangeProposal(**defaults)  # type: ignore[arg-type]
    proposals.add(proposal)
    return proposal


def test_configure_vault_sets_the_path(client: TestClient, tmp_path: Path) -> None:
    new_vault = tmp_path / "other_vault"
    new_vault.mkdir()

    response = client.post("/api/v1/vault/configure", json={"path": str(new_vault)})

    assert response.status_code == 200
    assert response.json()["vault_path"] == str(new_vault)


def test_configure_vault_rejects_unusable_path(client: TestClient, tmp_path: Path) -> None:
    response = client.post("/api/v1/vault/configure", json={"path": str(tmp_path / "missing")})

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "VAULT_UNAVAILABLE"


def test_scan_vault_indexes_files(client: TestClient, vault_dir: Path) -> None:
    (vault_dir / "note.md").write_text("# Note\n")

    response = client.post("/api/v1/vault/scan")

    assert response.status_code == 200
    body = response.json()
    assert body["files_scanned"] == 1
    assert body["changed_files"] == 1
    assert body["errors"] == []


def test_list_changes_returns_only_pending(
    client: TestClient, proposals: ChangeProposalRepository
) -> None:
    _seed_proposal(proposals, id="pending_1")
    _seed_proposal(proposals, id="applied_1", status=ProposalStatus.APPLIED)

    response = client.get("/api/v1/vault/changes")

    assert response.status_code == 200
    ids = {c["id"] for c in response.json()["changes"]}
    assert ids == {"pending_1"}


def test_apply_change_approves_and_writes_it(
    client: TestClient, proposals: ChangeProposalRepository, vault_dir: Path
) -> None:
    _seed_proposal(proposals, path="new_note.md", content="# Brand new\n")

    response = client.post("/api/v1/vault/changes/proposal_1/apply")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "applied"
    assert (vault_dir / "new_note.md").read_text() == "# Brand new\n"


def test_apply_change_404s_when_missing(client: TestClient) -> None:
    response = client.post("/api/v1/vault/changes/missing/apply")

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_apply_change_conflicts_when_already_applied(
    client: TestClient, proposals: ChangeProposalRepository
) -> None:
    _seed_proposal(proposals, status=ProposalStatus.APPLIED)

    response = client.post("/api/v1/vault/changes/proposal_1/apply")

    assert response.status_code == 409
    assert response.json()["detail"]["error"]["code"] == "CONFLICT"


def test_reject_change_marks_it_rejected(
    client: TestClient, proposals: ChangeProposalRepository
) -> None:
    _seed_proposal(proposals)

    response = client.post("/api/v1/vault/changes/proposal_1/reject")

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_reject_change_404s_when_missing(client: TestClient) -> None:
    response = client.post("/api/v1/vault/changes/missing/reject")

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_search_vault_finds_matching_note(client: TestClient, vault_dir: Path) -> None:
    (vault_dir / "window_functions.md").write_text(
        "# Window Functions\n\nA window function computes a value across a set of rows.\n"
    )
    (vault_dir / "subqueries.md").write_text(
        "# Subqueries\n\nA subquery is nested inside another.\n"
    )
    client.post("/api/v1/vault/scan")

    response = client.get("/api/v1/vault/search", params={"q": "window function"})

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["path"] == "window_functions.md"
    assert results[0]["title"] == "Window Functions"
    assert "window" in results[0]["snippet"].lower()


def test_search_vault_rejects_a_blank_query(client: TestClient) -> None:
    response = client.get("/api/v1/vault/search", params={"q": "   "})

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "VALIDATION_ERROR"


def test_search_vault_excludes_missing_files(client: TestClient, vault_dir: Path) -> None:
    note = vault_dir / "note.md"
    note.write_text("# Note\n\nContent about elephants.\n")
    client.post("/api/v1/vault/scan")
    note.unlink()
    client.post("/api/v1/vault/scan")

    response = client.get("/api/v1/vault/search", params={"q": "elephants"})

    assert response.status_code == 200
    assert response.json()["results"] == []
