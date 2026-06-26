import json
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db.models import Base
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_UIR = ROOT / "examples" / "production_like" / "uir" / "policy"


@pytest.fixture
def execution_client(tmp_path) -> Iterator[tuple[TestClient, Path]]:
    from app.api.deps import get_db, get_storage_service
    from app.services.storage_service import StorageService

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    storage_root = tmp_path / "storage"
    app = create_app(Settings(storage_root=str(storage_root), database_url="sqlite:///unused.db"))

    def override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage_service] = lambda: StorageService(storage_root)

    with TestClient(app) as client:
        yield client, storage_root


def import_policy_document(client: TestClient, filename: str) -> str:
    uir = json.loads((PRODUCTION_UIR / filename).read_text(encoding="utf-8"))
    response = client.post("/api/v1/documents/import", json={"uir": uir})
    assert response.status_code == 200
    return response.json()["doc_id"]


def create_policy_task(client: TestClient, doc_id: str, schema_id: str = "policy_doc") -> str:
    response = client.post(
        "/api/v1/tasks",
        json={
            "doc_id": doc_id,
            "schema_id": schema_id,
            "template_id": "policy_doc_base_v1",
            "schema_version": "1.0.0",
            "template_version": "1.0.0",
            "options": {"enable_llm_fallback": False},
        },
    )
    assert response.status_code == 200
    return response.json()["task_id"]


def test_execute_task_runs_service_pipeline_and_updates_detail(execution_client):
    client, _storage_root = execution_client
    doc_id = import_policy_document(client, "policy_001_standard.json")
    task_id = create_policy_task(client, doc_id)

    response = client.post(f"/api/v1/tasks/{task_id}/execute")

    assert response.status_code == 200
    executed = response.json()
    assert executed["task_id"] == task_id
    assert executed["status"] == "completed"
    assert executed["review_required_count"] == 0
    assert executed["unmapped_required_count"] == 0
    assert Path(executed["package_zip_path"]).is_file()

    report_paths = executed["report_paths"]
    assert Path(report_paths["mapping_report"]).is_file()
    assert Path(report_paths["validation_report"]).is_file()
    assert Path(report_paths["content_organization_report"]).is_file()
    assert Path(report_paths["chunks"]).is_file()

    content_org_response = client.get(f"/api/v1/tasks/{task_id}/reports/content-organization")
    assert content_org_response.status_code == 200
    assert content_org_response.json()["chunk_count"] > 0

    chunks_response = client.get(f"/api/v1/tasks/{task_id}/reports/chunks")
    assert chunks_response.status_code == 200
    chunks_report = chunks_response.json()
    assert chunks_report["total"] > 0
    assert chunks_report["items"][0]["summary"]

    package_dir = Path(executed["package_zip_path"]).parent
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest_paths = {file["path"] for file in manifest["files"]}
    assert "content_organization_report.json" in manifest_paths

    with zipfile.ZipFile(executed["package_zip_path"]) as archive:
        assert "content_organization_report.json" in archive.namelist()

    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == "completed"
    assert detail["package_zip_path"] == executed["package_zip_path"]
    assert detail["report_paths"] == report_paths


def test_execute_task_marks_review_required_for_alias_variants(execution_client):
    client, _storage_root = execution_client
    doc_id = import_policy_document(client, "policy_002_alias_variants.json")
    task_id = create_policy_task(client, doc_id)

    response = client.post(f"/api/v1/tasks/{task_id}/execute")

    assert response.status_code == 200
    executed = response.json()
    assert executed["status"] == "review_required"
    assert executed["review_required_count"] > 0
    assert Path(executed["package_zip_path"]).is_file()


def test_execute_task_returns_404_and_marks_failed_for_missing_schema(execution_client):
    client, _storage_root = execution_client
    doc_id = import_policy_document(client, "policy_001_standard.json")
    task_id = create_policy_task(client, doc_id, schema_id="missing_schema")

    response = client.post(f"/api/v1/tasks/{task_id}/execute")

    assert response.status_code == 404
    assert response.json()["detail"] == "schema not found: missing_schema"

    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "failed"
