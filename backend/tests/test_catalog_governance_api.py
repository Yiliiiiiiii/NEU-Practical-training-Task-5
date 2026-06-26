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
PRODUCTION_LIKE_DIR = ROOT / "examples" / "production_like"
SCHEMAS_DIR = PRODUCTION_LIKE_DIR / "schemas"
TEMPLATES_DIR = PRODUCTION_LIKE_DIR / "mapping_templates"
UIR_DIR = PRODUCTION_LIKE_DIR / "uir" / "policy"


@pytest.fixture
def catalog_client(tmp_path) -> Iterator[TestClient]:
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


def load_policy_schema(version: str = "1.1.0") -> dict:
    data = json.loads((SCHEMAS_DIR / "policy_doc_v1.json").read_text(encoding="utf-8"))
    data["version"] = version
    data["description"] = "Governed test schema version"
    return data


def load_policy_template(version: str = "1.1.0") -> dict:
    data = json.loads((TEMPLATES_DIR / "policy_doc_base_v1.json").read_text(encoding="utf-8"))
    data["version"] = version
    data["aliases"]["title"] = [*data["aliases"]["title"], "治理标题"]
    return data


def import_policy_document(client: TestClient) -> str:
    uir = json.loads((UIR_DIR / "policy_001_standard.json").read_text(encoding="utf-8"))
    response = client.post("/api/v1/documents/import", json={"uir": uir})
    assert response.status_code == 200
    return response.json()["doc_id"]


def create_task(
    client: TestClient,
    doc_id: str,
    schema_version: str = "1.0.0",
    template_version: str = "1.0.0",
) -> str:
    response = client.post(
        "/api/v1/tasks",
        json={
            "doc_id": doc_id,
            "schema_id": "policy_doc",
            "template_id": "policy_doc_base_v1",
            "schema_version": schema_version,
            "template_version": template_version,
        },
    )
    assert response.status_code == 200
    return response.json()["task_id"]


def test_catalog_lists_seeded_schema_template_versions(catalog_client):
    schemas = catalog_client.get("/api/v1/schemas")
    templates = catalog_client.get("/api/v1/templates")

    assert schemas.status_code == 200
    assert any(
        item["schema_id"] == "policy_doc"
        and item["version"] == "1.0.0"
        and item["status"] == "active"
        and item["content_hash"].startswith("sha256:")
        for item in schemas.json()["items"]
    )
    assert templates.status_code == 200
    assert any(
        item["template_id"] == "policy_doc_base_v1"
        and item["version"] == "1.0.0"
        and item["status"] == "active"
        and item["content_hash"].startswith("sha256:")
        for item in templates.json()["items"]
    )


def test_catalog_create_activate_archive_versions(catalog_client):
    create_schema = catalog_client.post(
        "/api/v1/schemas",
        json={"schema": load_policy_schema(), "status": "draft"},
    )
    assert create_schema.status_code == 200
    assert create_schema.json()["status"] == "draft"

    activate_schema = catalog_client.post("/api/v1/schemas/policy_doc/versions/1.1.0/activate")
    assert activate_schema.status_code == 200
    assert activate_schema.json()["status"] == "active"

    archive_schema = catalog_client.post("/api/v1/schemas/policy_doc/versions/1.1.0/archive")
    assert archive_schema.status_code == 200
    assert archive_schema.json()["status"] == "archived"

    create_template = catalog_client.post(
        "/api/v1/templates",
        json={"template": load_policy_template(), "status": "draft"},
    )
    assert create_template.status_code == 200
    assert create_template.json()["status"] == "draft"

    activate_template = catalog_client.post(
        "/api/v1/templates/policy_doc_base_v1/versions/1.1.0/activate"
    )
    assert activate_template.status_code == 200
    assert activate_template.json()["status"] == "active"

    archive_template = catalog_client.post(
        "/api/v1/templates/policy_doc_base_v1/versions/1.1.0/archive"
    )
    assert archive_template.status_code == 200
    assert archive_template.json()["status"] == "archived"


def test_referenced_versions_cannot_be_archived_and_snapshot_keeps_versions(catalog_client):
    doc_id = import_policy_document(catalog_client)
    task_id = create_task(catalog_client, doc_id)
    executed = catalog_client.post(f"/api/v1/tasks/{task_id}/execute")
    assert executed.status_code == 200

    archive_schema = catalog_client.post("/api/v1/schemas/policy_doc/versions/1.0.0/archive")
    archive_template = catalog_client.post(
        "/api/v1/templates/policy_doc_base_v1/versions/1.0.0/archive"
    )
    assert archive_schema.status_code == 400
    assert archive_template.status_code == 400

    detail = catalog_client.get(f"/api/v1/tasks/{task_id}").json()
    assert detail["schema_version"] == "1.0.0"
    assert detail["template_version"] == "1.0.0"


def test_archived_template_version_is_not_usable_for_new_execution(catalog_client):
    create_template = catalog_client.post(
        "/api/v1/templates",
        json={"template": load_policy_template(), "status": "draft"},
    )
    assert create_template.status_code == 200
    archive_template = catalog_client.post(
        "/api/v1/templates/policy_doc_base_v1/versions/1.1.0/archive"
    )
    assert archive_template.status_code == 200

    doc_id = import_policy_document(catalog_client)
    task_id = create_task(
        catalog_client,
        doc_id,
        schema_version="1.0.0",
        template_version="1.1.0",
    )
    executed = catalog_client.post(f"/api/v1/tasks/{task_id}/execute")

    assert executed.status_code == 404
    assert executed.json()["detail"] == "template not found: policy_doc_base_v1"
