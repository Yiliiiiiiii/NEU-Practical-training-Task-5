import hashlib
import io
import json
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.config import Settings
from app.db.models import Base
from app.main import create_app
from app.services.storage_service import StorageService

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "demo"


@pytest.fixture()
def api_e2e_client(tmp_path) -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    storage = StorageService(tmp_path / "storage")
    app = create_app(
        Settings(storage_root=str(storage.root), database_url="sqlite:///unused.db"),
        init_database=False,
    )

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[deps.get_db] = override_db
    app.dependency_overrides[deps.get_storage_service] = lambda: storage
    with TestClient(app) as client:
        yield client


def _load(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def _assert_ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def _run_full_api_pipeline(
    client: TestClient,
    uir_name: str,
    schema_name: str,
    template_name: str,
) -> tuple[str, dict, bytes]:
    uir = _load(uir_name)
    schema = _load(schema_name)
    template = _load(template_name)

    imported = _assert_ok(client.post("/api/v1/documents/import", json={"uir": uir}))
    assert imported["doc_id"] == uir["doc_id"]
    _assert_ok(client.post("/api/v1/schemas", json={"schema": schema}))
    _assert_ok(client.post("/api/v1/templates", json={"template": template}))

    task = _assert_ok(
        client.post(
            "/api/v1/tasks",
            json={
                "doc_id": uir["doc_id"],
                "schema_id": schema["schema_id"],
                "template_id": template["template_id"],
                "schema_version": schema["version"],
                "template_version": template["version"],
                "options": {"chunk_size": 128, "enable_llm_fallback": False},
            },
        )
    )
    task_id = task["task_id"]

    candidates = _assert_ok(
        client.post(
            f"/api/v1/tasks/{task_id}/generate-candidates",
            json={"include_metadata": True, "include_blocks": True, "include_tables": True},
        )
    )
    assert candidates["candidate_count"] > 0
    mapping = _assert_ok(
        client.post(
            f"/api/v1/tasks/{task_id}/map",
            json={"review_threshold": 0.0, "enable_llm_fallback": False},
        )
    )
    assert mapping["status"] == "mapping_completed"

    converted = _assert_ok(
        client.post(
            f"/api/v1/tasks/{task_id}/convert",
            json={"render_outputs": True, "chunk_size": 128},
        )
    )
    assert converted["status"] == "rendered"
    assert set(converted["outputs"]) == {"content.json", "content.md", "chunks.json"}

    canonical = _assert_ok(client.get(f"/api/v1/tasks/{task_id}/canonical"))
    assert canonical["task_id"] == task_id
    assert canonical["doc_id"] == uir["doc_id"]
    assert canonical["blocks"]

    package = _assert_ok(
        client.post(
            f"/api/v1/tasks/{task_id}/package",
            json={"package_version": "9.0.0-test"},
        )
    )
    assert package["status"] == "completed"
    download = client.get(f"/api/v1/tasks/{task_id}/package/download")
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/zip"
    assert download.headers["X-SHA256"] == hashlib.sha256(download.content).hexdigest()

    validation = _assert_ok(client.get(f"/api/v1/tasks/{task_id}/reports/validation"))
    consistency = _assert_ok(client.get(f"/api/v1/tasks/{task_id}/reports/consistency"))
    trace = _assert_ok(client.get(f"/api/v1/tasks/{task_id}/trace"))
    assert validation["passed"] is True
    assert consistency["passed"] is True
    assert trace["events"]

    return task_id, canonical, download.content


def _assert_standard_package(zip_bytes: bytes, task_id: str) -> dict:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = set(archive.namelist())
        required = {
            "chunks.json",
            "config_snapshot.json",
            "consistency_report.json",
            "content.json",
            "content.md",
            "manifest.json",
            "mapping_report.json",
            "metadata.json",
            "trace.json",
            "validation_report.json",
        }
        assert required <= names
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["task_id"] == task_id
        assert manifest["package_version"] == "9.0.0-test"
        assert "manifest.json" not in {entry["path"] for entry in manifest["files"]}
        for entry in manifest["files"]:
            raw = archive.read(entry["path"])
            assert len(raw) == entry["bytes"]
            assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        return json.loads(archive.read("content.json"))


def test_general_document_true_api_e2e(api_e2e_client):
    task_id, canonical, zip_bytes = _run_full_api_pipeline(
        api_e2e_client,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )

    content = _assert_standard_package(zip_bytes, task_id)
    assert content["doc_id"] == "doc_demo_general_001"
    assert content["data"]["title"]
    assert content["data"]["language"] == "zh-CN"
    assert canonical["fields"]["title"]["source_candidates"]


def test_policy_document_true_api_e2e(api_e2e_client):
    task_id, canonical, zip_bytes = _run_full_api_pipeline(
        api_e2e_client,
        "example_uir_policy_doc.json",
        "target_schema_policy.json",
        "mapping_template_policy.json",
    )

    content = _assert_standard_package(zip_bytes, task_id)
    assert content["doc_id"] == "doc_demo_policy_001"
    assert content["data"]["publish_date"] == "2026-06-01"
    assert content["data"]["main_content"]
    assert canonical["fields"]["main_content"]["source_blocks"] == [
        "blk_p_005",
        "blk_p_006",
    ]


def _zip_payload(zip_bytes: bytes, name: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        return archive.read(name)


def test_full_pipeline_retries_replace_current_records_and_keep_render_bytes_stable(
    api_e2e_client,
):
    task_id, _, first_zip = _run_full_api_pipeline(
        api_e2e_client,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )
    first_package_id = json.loads(_zip_payload(first_zip, "manifest.json"))["package_id"]

    reimport = _assert_ok(
        api_e2e_client.post(
            "/api/v1/documents/import",
            json={"uir": _load("example_uir_general_doc.json")},
        )
    )
    assert reimport["doc_id"] == "doc_demo_general_001"
    assert _assert_ok(api_e2e_client.get("/api/v1/documents"))["total"] == 1

    candidate_counts = []
    for _ in range(2):
        candidate_counts.append(
            _assert_ok(
                api_e2e_client.post(f"/api/v1/tasks/{task_id}/generate-candidates", json={})
            )["candidate_count"]
        )
    assert candidate_counts[0] == candidate_counts[1]
    candidates = _assert_ok(api_e2e_client.get(f"/api/v1/tasks/{task_id}/candidates"))
    assert len(candidates["items"]) == candidate_counts[-1]

    mapped_counts = []
    for _ in range(2):
        mapped_counts.append(
            _assert_ok(
                api_e2e_client.post(
                    f"/api/v1/tasks/{task_id}/map",
                    json={"review_threshold": 0.0, "enable_llm_fallback": False},
                )
            )["mapped_count"]
        )
    assert mapped_counts[0] == mapped_counts[1]
    mappings = _assert_ok(api_e2e_client.get(f"/api/v1/tasks/{task_id}/mappings"))
    assert len(mappings["items"]) == mapped_counts[-1]

    for _ in range(2):
        converted = _assert_ok(
            api_e2e_client.post(
                f"/api/v1/tasks/{task_id}/convert",
                json={"render_outputs": True, "chunk_size": 128},
            )
        )
        assert converted["status"] == "rendered"

    second_package = _assert_ok(
        api_e2e_client.post(f"/api/v1/tasks/{task_id}/package", json={})
    )
    third_package = _assert_ok(
        api_e2e_client.post(f"/api/v1/tasks/{task_id}/package", json={})
    )
    assert len({first_package_id, second_package["package_id"], third_package["package_id"]}) == 3

    latest = api_e2e_client.get(f"/api/v1/tasks/{task_id}/package/download")
    assert latest.status_code == 200
    latest_manifest = json.loads(_zip_payload(latest.content, "manifest.json"))
    assert latest_manifest["package_id"] == third_package["package_id"]
    for name in ("content.json", "content.md", "chunks.json"):
        assert _zip_payload(first_zip, name) == _zip_payload(latest.content, name)
