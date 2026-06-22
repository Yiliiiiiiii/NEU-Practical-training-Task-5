import json
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
DEMO_DIR = ROOT / "examples" / "demo"


@pytest.fixture
def mapping_client(tmp_path) -> Iterator[TestClient]:
    from app.api.deps import get_db, get_storage_service
    from app.services.storage_service import StorageService

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    storage_root = tmp_path / "storage"
    app = create_app(
        Settings(storage_root=str(storage_root), database_url="sqlite:///unused.db"),
        init_database=False,
    )

    def override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage_service] = lambda: StorageService(storage_root)

    with TestClient(app) as client:
        yield client


def load_json(name: str) -> dict:
    return json.loads((DEMO_DIR / name).read_text(encoding="utf-8"))


def prepare_general_task(client: TestClient) -> str:
    assert client.post(
        "/api/v1/documents/import",
        json={"uir": load_json("example_uir_general_doc.json")},
    ).status_code == 200
    assert client.post(
        "/api/v1/schemas",
        json={"schema": load_json("target_schema_general.json")},
    ).status_code == 200
    assert client.post(
        "/api/v1/templates",
        json={"template": load_json("mapping_template_general.json")},
    ).status_code == 200
    response = client.post(
        "/api/v1/tasks",
        json={
            "doc_id": "doc_demo_general_001",
            "schema_id": "schema_general_v1",
            "template_id": "tpl_general_v1",
        },
    )
    assert response.status_code == 200
    return response.json()["task_id"]


def test_generate_candidates_from_demo_uir(mapping_client):
    task_id = prepare_general_task(mapping_client)

    response = mapping_client.post(f"/api/v1/tasks/{task_id}/generate-candidates")
    candidates_response = mapping_client.get(f"/api/v1/tasks/{task_id}/candidates")
    task_response = mapping_client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "candidates_ready"
    assert response.json()["candidate_count"] >= 6
    assert candidates_response.status_code == 200
    candidates = candidates_response.json()["items"]
    source_paths = {candidate["source_path"] for candidate in candidates}
    source_names = {candidate["source_name"] for candidate in candidates}
    assert "metadata.文档标题" in source_paths
    assert "metadata.创建日期" in source_paths
    assert "blocks.blk_g_001.text" in source_paths
    assert "创建日期" in source_names
    assert task_response.json()["status"] == "candidates_ready"


def test_execute_rule_mapping_and_get_report(mapping_client):
    task_id = prepare_general_task(mapping_client)
    mapping_client.post(f"/api/v1/tasks/{task_id}/generate-candidates")

    response = mapping_client.post(
        f"/api/v1/tasks/{task_id}/map",
        json={"enable_llm_fallback": False, "review_threshold": 0.8},
    )
    mappings_response = mapping_client.get(f"/api/v1/tasks/{task_id}/mappings")
    report_response = mapping_client.get(f"/api/v1/tasks/{task_id}/reports/mapping")

    assert response.status_code == 200
    assert response.json()["mapped_count"] >= 4
    assert response.json()["status"] in {"mapping_completed", "review_required"}
    assert mappings_response.status_code == 200
    mappings = mappings_response.json()["items"]
    by_target = {mapping["target_field_id"]: mapping for mapping in mappings}
    assert by_target["title"]["method"] == "alias_match"
    assert by_target["author"]["method"] == "alias_match"
    assert by_target["created_date"]["target_field_id"] == "created_date"
    assert by_target["summary"]["method"] in {"exact_match", "alias_match"}
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["summary"]["mapped_fields"] >= 4
    assert "language" in report["unmapped"]


def test_review_updates_low_confidence_mapping(mapping_client):
    task_id = prepare_general_task(mapping_client)
    mapping_client.post(f"/api/v1/tasks/{task_id}/generate-candidates")
    mapping_client.post(
        f"/api/v1/tasks/{task_id}/map",
        json={"enable_llm_fallback": False, "review_threshold": 0.99},
    )

    mappings = mapping_client.get(f"/api/v1/tasks/{task_id}/mappings").json()["items"]
    reviewed_mapping = next(
        mapping for mapping in mappings if mapping["target_field_id"] == "title"
    )
    assert reviewed_mapping["need_review"] is True

    response = mapping_client.post(
        f"/api/v1/tasks/{task_id}/mappings/review",
        json={
            "reviews": [
                {
                    "mapping_id": reviewed_mapping["mapping_id"],
                    "new_target_field_id": "title",
                    "decision": "confirmed",
                    "comment": "人工确认标题映射",
                }
            ]
        },
    )
    updated = mapping_client.get(f"/api/v1/tasks/{task_id}/mappings").json()["items"]
    title_mapping = next(
        mapping
        for mapping in updated
        if mapping["mapping_id"] == reviewed_mapping["mapping_id"]
    )

    assert response.status_code == 200
    assert response.json() == {"task_id": task_id, "updated": 1, "status": "review_saved"}
    assert title_mapping["status"] == "confirmed"
    assert title_mapping["need_review"] is False
