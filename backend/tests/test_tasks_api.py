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
DEMO_UIR = ROOT / "examples" / "demo" / "example_uir_general_doc.json"


@pytest.fixture
def tasks_client(tmp_path) -> Iterator[TestClient]:
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
        yield client


def load_demo_uir() -> dict:
    return json.loads(DEMO_UIR.read_text(encoding="utf-8"))


def import_demo_document(client: TestClient) -> None:
    response = client.post("/api/v1/documents/import", json={"uir": load_demo_uir()})
    assert response.status_code == 200


def test_create_task_and_get_status(tasks_client):
    import_demo_document(tasks_client)

    response = tasks_client.post(
        "/api/v1/tasks",
        json={
            "doc_id": "doc_demo_general_001",
            "schema_id": "schema_general_v1",
            "template_id": "tpl_general_v1",
            "schema_version": "1.0.0",
            "template_version": "1.0.0",
            "options": {"chunk_size": 800, "enable_llm_fallback": False},
        },
    )

    assert response.status_code == 200
    created = response.json()
    assert created["task_id"].startswith("task_")
    assert created["status"] == "created"

    detail_response = tasks_client.get(f"/api/v1/tasks/{created['task_id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["task_id"] == created["task_id"]
    assert detail["status"] == "created"
    assert detail["doc_id"] == "doc_demo_general_001"
    assert detail["schema_id"] == "schema_general_v1"
    assert detail["template_id"] == "tpl_general_v1"
    assert detail["input_hash"].startswith("sha256:")


def test_list_tasks_includes_created_task(tasks_client):
    import_demo_document(tasks_client)
    created = tasks_client.post(
        "/api/v1/tasks",
        json={
            "doc_id": "doc_demo_general_001",
            "schema_id": "schema_general_v1",
            "template_id": "tpl_general_v1",
        },
    ).json()

    response = tasks_client.get("/api/v1/tasks")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["task_id"] == created["task_id"]


def test_create_task_returns_404_for_unknown_document(tasks_client):
    response = tasks_client.post(
        "/api/v1/tasks",
        json={
            "doc_id": "missing_doc",
            "schema_id": "schema_general_v1",
            "template_id": "tpl_general_v1",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "document not found"


def test_task_detail_returns_404_for_unknown_task(tasks_client):
    response = tasks_client.get("/api/v1/tasks/missing_task")

    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"
