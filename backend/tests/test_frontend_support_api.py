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
PRODUCTION_UIR = ROOT / "examples" / "production_like" / "uir" / "policy"


@pytest.fixture
def frontend_api_client(tmp_path) -> Iterator[TestClient]:
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


def import_and_execute_policy_task(client: TestClient) -> str:
    uir = json.loads((PRODUCTION_UIR / "policy_001_standard.json").read_text(encoding="utf-8"))
    import_response = client.post("/api/v1/documents/import", json={"uir": uir})
    assert import_response.status_code == 200
    task_response = client.post(
        "/api/v1/tasks",
        json={
            "doc_id": uir["doc_id"],
            "schema_id": "policy_doc",
            "template_id": "policy_doc_base_v1",
        },
    )
    assert task_response.status_code == 200
    task_id = task_response.json()["task_id"]
    execute_response = client.post(f"/api/v1/tasks/{task_id}/execute")
    assert execute_response.status_code == 200
    return task_id


def test_schema_and_template_catalog_apis(frontend_api_client):
    schemas = frontend_api_client.get("/api/v1/schemas")
    templates = frontend_api_client.get("/api/v1/templates")
    schema = frontend_api_client.get("/api/v1/schemas/policy_doc")
    template = frontend_api_client.get("/api/v1/templates/policy_doc_base_v1")

    assert schemas.status_code == 200
    assert {item["schema_id"] for item in schemas.json()["items"]} >= {"policy_doc"}
    assert templates.status_code == 200
    assert {item["template_id"] for item in templates.json()["items"]} >= {
        "policy_doc_base_v1"
    }
    assert schema.status_code == 200
    assert schema.json()["schema_id"] == "policy_doc"
    assert template.status_code == 200
    assert template.json()["schema_id"] == "policy_doc"


def test_task_report_and_package_apis(frontend_api_client):
    task_id = import_and_execute_policy_task(frontend_api_client)

    mapping = frontend_api_client.get(f"/api/v1/tasks/{task_id}/reports/mapping")
    validation = frontend_api_client.get(f"/api/v1/tasks/{task_id}/reports/validation")
    package = frontend_api_client.get(f"/api/v1/tasks/{task_id}/package")
    download = frontend_api_client.get(f"/api/v1/tasks/{task_id}/package/download")

    assert mapping.status_code == 200
    assert mapping.json()["task_id"] == task_id
    assert mapping.json()["mappings"]
    assert validation.status_code == 200
    assert validation.json()["task_id"] == task_id
    assert validation.json()["passed"] is True
    assert package.status_code == 200
    assert package.json()["task_id"] == task_id
    assert package.json()["status"] == "completed"
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/zip"
