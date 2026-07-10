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
from tests.topic5_helpers import announcement_uir

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


def create_policy_task(
    client: TestClient,
    doc_id: str,
    schema_id: str = "policy_doc",
    options: dict | None = None,
) -> str:
    response = client.post(
        "/api/v1/tasks",
        json={
            "doc_id": doc_id,
            "schema_id": schema_id,
            "template_id": "policy_doc_base_v1",
            "schema_version": "1.0.0",
            "template_version": "1.0.0",
            "options": {"enable_llm_fallback": False, **(options or {})},
        },
    )
    assert response.status_code == 200
    return response.json()["task_id"]


def create_schema_pack_task(
    client: TestClient,
    schema_pack_id: str,
    uir: dict,
    *,
    options: dict | None = None,
) -> str:
    imported = client.post("/api/v1/documents/import", json={"uir": uir})
    assert imported.status_code == 200
    created = client.post(
        "/api/v1/tasks",
        json={
            "doc_id": imported.json()["doc_id"],
            "schema_id": schema_pack_id,
            "template_id": f"{schema_pack_id}_base_v1",
            "schema_version": "1.0.0",
            "template_version": "1.0.0",
            "schema_pack_id": schema_pack_id,
            "options": options or {},
        },
    )
    assert created.status_code == 200
    return created.json()["task_id"]


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


def test_task_manifest_report_lists_verified_files(execution_client):
    client, _storage_root = execution_client
    doc_id = import_policy_document(client, "policy_001_standard.json")
    task_id = create_policy_task(client, doc_id)
    assert client.post(f"/api/v1/tasks/{task_id}/execute").status_code == 200

    response = client.get(f"/api/v1/tasks/{task_id}/reports/manifest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["files"]
    assert all("sha256" in item for item in payload["files"])


def test_registered_schema_pack_applies_metadata_template(execution_client):
    client, _storage_root = execution_client
    task_id = create_schema_pack_task(client, "announcement_doc", announcement_uir())

    response = client.post(f"/api/v1/tasks/{task_id}/execute")

    assert response.status_code == 200, response.text
    report_paths = response.json()["report_paths"]
    content = json.loads(Path(report_paths["content_json"]).read_text(encoding="utf-8"))
    metadata_report = json.loads(
        Path(report_paths["metadata_template_report"]).read_text(encoding="utf-8")
    )
    assert content["document_metadata"] == {
        "language": "zh-CN",
        "source": "example",
    }
    assert metadata_report["passed"] is True
    chunks = json.loads(Path(report_paths["chunks"]).read_text(encoding="utf-8"))[
        "items"
    ]
    assert any("maintenance" in chunk["content_tags"] for chunk in chunks)
    assert all("domain:campus" in chunk["management_tags"] for chunk in chunks)
    assert all(
        not any(
            tag.startswith(("task:", "doc:", "chunk_index:"))
            for tag in chunk["management_tags"]
        )
        for chunk in chunks
    )
    summary = content["document_summary"]
    content_org = json.loads(
        Path(report_paths["content_organization_report"]).read_text(encoding="utf-8")
    )
    assert summary["text"]
    assert summary["faithfulness_passed"] is True
    assert content_org["document_summary"] == summary


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


def test_execution_snapshot_records_only_safe_llm_config(execution_client):
    client, storage_root = execution_client
    secret = "phase28-snapshot-secret"
    doc_id = import_policy_document(client, "policy_001_standard.json")
    task_id = create_policy_task(
        client,
        doc_id,
        options={"llm_api_key": secret, "strict_llm": False},
    )

    response = client.post(f"/api/v1/tasks/{task_id}/execute")
    snapshot = json.loads(
        (storage_root / "tasks" / task_id / "execution_snapshot.json").read_text(
            encoding="utf-8"
        )
    )

    assert response.status_code == 200
    assert snapshot["llm"]["task_requested"] is False
    assert snapshot["llm"]["strict_failure"] is False
    assert snapshot["llm"]["max_suggestions_per_task"] == 20
    assert "api_key" not in snapshot["llm"]
    assert secret not in json.dumps(snapshot, ensure_ascii=False)


def test_task_execute_with_content_organization_options(execution_client):
    client, _storage_root = execution_client
    doc_id = import_policy_document(client, "policy_001_standard.json")
    task_id = create_policy_task(
        client,
        doc_id,
        options={
            "content_organization": {
                "chunk_strategy": "parent_child",
                "target_tokens": 64,
                "min_tokens": 1,
                "max_tokens": 128,
                "overlap_tokens": 0,
                "protect_tables": True,
                "protect_lists": True,
                "protect_code_blocks": True,
                "enable_parent_child": True,
            }
        },
    )

    response = client.post(f"/api/v1/tasks/{task_id}/execute")

    assert response.status_code == 200
    content_org = client.get(f"/api/v1/tasks/{task_id}/reports/content-organization").json()
    chunks = client.get(f"/api/v1/tasks/{task_id}/reports/chunks").json()["items"]
    assert content_org["summary"]["strategy"] == "parent_child"
    assert content_org["summary"]["parent_chunk_count"] > 0
    assert content_org["summary"]["child_chunk_count"] > 0
    assert any(chunk.get("granularity") == "parent" for chunk in chunks)
    assert any(
        chunk.get("parent_chunk_id")
        for chunk in chunks
        if chunk.get("granularity") == "child"
    )


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


def test_registered_task_executes_selected_schema_pack_and_persists_assertions(
    execution_client,
):
    client, storage_root = execution_client
    pack_dir = ROOT / "schema_packs" / "examples" / "announcement_doc"
    uir = json.loads(
        (pack_dir / "examples" / "example_001_uir.json").read_text(encoding="utf-8")
    )
    task_id = create_schema_pack_task(
        client,
        "announcement_doc",
        uir,
        options={"include_assertion_report_in_package": True},
    )

    executed = client.post(f"/api/v1/tasks/{task_id}/execute")

    assert executed.status_code == 200
    payload = executed.json()
    assert payload["status"] == "completed"
    assertion_path = Path(payload["report_paths"]["conversion_assertion_report"])
    assert assertion_path == (
        storage_root / "tasks" / task_id / "conversion_assertion_report.json"
    )
    assert assertion_path.is_file()
    snapshot = json.loads(
        (storage_root / "tasks" / task_id / "execution_snapshot.json").read_text(
            encoding="utf-8"
        )
    )
    assert snapshot["artifacts"]["conversion_assertion_report"] == str(
        assertion_path
    )

    report = client.get(f"/api/v1/tasks/{task_id}/reports/assertions")
    assert report.status_code == 200
    assert report.json()["passed"] is True

    package_dir = Path(payload["package_zip_path"]).parent
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    assertion_entry = next(
        item
        for item in manifest["files"]
        if item["path"] == "reports/conversion_assertion_report.json"
    )
    assert assertion_entry["required"] is False

    original_report = assertion_path.read_bytes()
    repeated = client.post(f"/api/v1/tasks/{task_id}/execute")
    assert repeated.status_code == 400
    assert "create a new task to rerun" in repeated.json()["detail"]
    assert assertion_path.read_bytes() == original_report


def test_registered_assertion_report_is_written_before_package_creation(
    execution_client,
    monkeypatch,
):
    from app.services.package_service import PackageService

    client, storage_root = execution_client
    pack_dir = ROOT / "schema_packs" / "examples" / "announcement_doc"
    uir = json.loads(
        (pack_dir / "examples" / "example_001_uir.json").read_text(encoding="utf-8")
    )
    task_id = create_schema_pack_task(client, "announcement_doc", uir)

    def fail_package_creation(*_args, **_kwargs):
        raise RuntimeError("forced package failure")

    monkeypatch.setattr(PackageService, "create_package", fail_package_creation)

    with pytest.raises(RuntimeError, match="forced package failure"):
        client.post(f"/api/v1/tasks/{task_id}/execute")

    report_path = (
        storage_root / "tasks" / task_id / "conversion_assertion_report.json"
    )
    assert report_path.is_file()
    assert json.loads(report_path.read_text(encoding="utf-8"))["schema_pack_id"] == (
        "announcement_doc"
    )
    report = client.get(f"/api/v1/tasks/{task_id}/reports/assertions")
    assert report.status_code == 200
    assert report.json()["schema_pack_id"] == "announcement_doc"
    snapshot = json.loads(
        (storage_root / "tasks" / task_id / "execution_snapshot.json").read_text(
            encoding="utf-8"
        )
    )
    assert snapshot["status"] == "failed"
    assert snapshot["artifacts"]["conversion_assertion_report"] == str(report_path)


def test_registered_strict_assertion_failure_has_truthful_diagnostic(
    execution_client,
):
    from app.db.models import ConversionTask

    client, storage_root = execution_client
    pack_dir = ROOT / "schema_packs" / "examples" / "event_notice_doc"
    uir = json.loads(
        (pack_dir / "badcases" / "badcase_001_uir.json").read_text(encoding="utf-8")
    )
    task_id = create_schema_pack_task(
        client,
        "event_notice_doc",
        uir,
        options={"strict_output_assertions": True},
    )

    executed = client.post(f"/api/v1/tasks/{task_id}/execute")

    assert executed.status_code == 200
    assert executed.json()["status"] == "failed"
    snapshot = json.loads(
        (storage_root / "tasks" / task_id / "execution_snapshot.json").read_text(
            encoding="utf-8"
        )
    )
    assert snapshot["package_verifier_passed"] is True

    engine = create_engine(f"sqlite:///{storage_root.parent / 'test.db'}")
    Session = sessionmaker(bind=engine)
    with Session() as db:
        task = db.get(ConversionTask, task_id)
        assert task is not None
        assert task.error_code == "output_assertion_failed"
        assert task.error_message == "strict output assertion failed"
