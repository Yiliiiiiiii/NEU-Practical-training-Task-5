import importlib.util
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db.models import Base
from app.main import create_app
from tests.test_task_execution_api import create_policy_task, import_policy_document

ROOT = Path(__file__).resolve().parents[2]
RETENTION_SCRIPT = ROOT / "scripts" / "retention_cleanup.py"


@pytest.fixture
def governance_client(tmp_path) -> Iterator[TestClient]:
    from app.api.deps import get_db, get_storage_service
    from app.services.storage_service import StorageService

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    storage_root = tmp_path / "storage"
    app = create_app(
        Settings(
            storage_root=str(storage_root),
            database_url="sqlite:///unused.db",
            api_key_auth_enabled=False,
            audit_log_enabled=True,
            _env_file=None,
        )
    )

    def override_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage_service] = lambda: StorageService(storage_root)

    with TestClient(app) as client:
        yield client


def make_auth_client(tmp_path, *, enabled: bool) -> TestClient:
    from app.api.deps import get_db

    database_url = f"sqlite:///{tmp_path / 'auth.db'}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    app = create_app(
        Settings(
            storage_root=str(tmp_path / "storage"),
            database_url=database_url,
            api_key_auth_enabled=enabled,
            api_keys="dev-key",
            _env_file=None,
        )
    )

    def override_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def test_api_key_auth_disabled_allows_existing_requests(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = make_auth_client(tmp_path, enabled=False)

    response = client.get("/api/v1/tasks")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_api_key_auth_enabled_rejects_missing_key(tmp_path):
    client = make_auth_client(tmp_path, enabled=True)

    response = client.get("/api/v1/tasks")
    health = client.get("/health")

    assert response.status_code == 401
    assert health.status_code == 200


def test_api_key_auth_enabled_accepts_valid_key(tmp_path):
    client = make_auth_client(tmp_path, enabled=True)

    response = client.get("/api/v1/tasks", headers={"X-API-Key": "dev-key"})

    assert response.status_code != 401


def test_audit_log_query_filters_by_entity(governance_client):
    response = governance_client.get("/api/v1/audit-logs")

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_audit_log_created_for_task_execute_and_package_download(governance_client):
    doc_id = import_policy_document(governance_client, "policy_001_standard.json")
    task_id = create_policy_task(governance_client, doc_id)

    execute = governance_client.post(f"/api/v1/tasks/{task_id}/execute")
    download = governance_client.get(f"/api/v1/tasks/{task_id}/package/download")
    logs = governance_client.get("/api/v1/audit-logs", params={"entity_id": task_id})

    assert execute.status_code == 200
    assert download.status_code == 200
    assert logs.status_code == 200
    actions = {item["action"] for item in logs.json()["items"]}
    assert "task.execute" in actions
    assert "package.download" in actions


def test_llm_api_key_not_in_reports_or_audit_logs(governance_client):
    secret = "phase28-super-secret"
    doc_id = import_policy_document(governance_client, "policy_001_standard.json")
    task_id = create_policy_task(
        governance_client,
        doc_id,
        options={
            "enable_llm_fallback": False,
            "llm_api_key": secret,
            "nested": {"api_key": secret},
        },
    )

    execute = governance_client.post(f"/api/v1/tasks/{task_id}/execute")
    detail = governance_client.get(f"/api/v1/tasks/{task_id}")
    mapping = governance_client.get(f"/api/v1/tasks/{task_id}/reports/mapping")
    logs = governance_client.get("/api/v1/audit-logs", params={"entity_id": task_id})

    assert execute.status_code == 200
    serialized = " ".join(
        [
            detail.text,
            mapping.text,
            logs.text,
        ]
    )
    assert secret not in serialized
    assert detail.json()["options"]["llm_api_key"] == "[REDACTED]"
    assert detail.json()["options"]["nested"]["api_key"] == "[REDACTED]"


def test_retention_cleanup_dry_run_does_not_delete(tmp_path):
    module = load_script(RETENTION_SCRIPT, "retention_cleanup")
    storage_root = tmp_path / "storage"
    old_file = storage_root / "packages" / "old.txt"
    old_file.parent.mkdir(parents=True)
    old_file.write_text("old", encoding="utf-8")

    result = module.cleanup_artifacts(storage_root, days=0, dry_run=True)

    assert result["matched_count"] == 1
    assert result["deleted_count"] == 0
    assert old_file.is_file()


def test_retention_cleanup_delete_removes_only_storage_files(tmp_path):
    module = load_script(RETENTION_SCRIPT, "retention_cleanup_delete")
    storage_root = tmp_path / "storage"
    old_file = storage_root / "packages" / "old.json"
    old_file.parent.mkdir(parents=True)
    old_file.write_text("old", encoding="utf-8")

    result = module.cleanup_artifacts(storage_root, days=0, dry_run=False)

    assert result["matched_count"] == 1
    assert result["deleted_count"] == 1
    assert not old_file.exists()


def load_script(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
