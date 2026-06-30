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
REAL_WORLD_PROCUREMENT = ROOT / "examples" / "real_world" / "uir" / "procurement"
EVAL_REAL_WORLD_UIR = ROOT / "scripts" / "eval_real_world_uir.py"


@pytest.fixture
def procurement_catalog_client(tmp_path: Path) -> Iterator[TestClient]:
    from app.api.deps import get_db, get_storage_service
    from app.services.storage_service import StorageService

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    storage_root = tmp_path / "storage"
    app = create_app(Settings(storage_root=str(storage_root), database_url="sqlite:///unused.db"))

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


def import_procurement_document(client: TestClient) -> str:
    uir = json.loads(
        (
            REAL_WORLD_PROCUREMENT
            / "real_procurement_001_broadcast_security_supervision.json"
        ).read_text(encoding="utf-8")
    )
    response = client.post("/api/v1/documents/import", json={"uir": uir})
    assert response.status_code == 200
    return response.json()["doc_id"]


def create_procurement_task(client: TestClient, doc_id: str) -> str:
    response = client.post(
        "/api/v1/tasks",
        json={
            "doc_id": doc_id,
            "schema_id": "procurement_doc",
            "schema_version": "1.0.0",
            "template_id": "procurement_doc_base_v1",
            "template_version": "1.0.0",
            "options": {"enable_llm_fallback": False},
        },
    )
    assert response.status_code == 200
    return response.json()["task_id"]


def test_procurement_schema_and_template_load() -> None:
    from app.services.schema_service import SchemaService
    from app.services.template_service import TemplateService

    schema = SchemaService(SCHEMAS_DIR).load_schema("procurement_doc", "1.0.0")
    template = TemplateService(TEMPLATES_DIR).load_template(
        "procurement_doc_base_v1",
        "1.0.0",
    )

    fields = {field.field_id for field in schema.fields}
    assert schema.schema_id == "procurement_doc"
    assert {field.field_id for field in schema.fields if field.required} == {
        "title",
        "project_name",
        "purchaser",
    }
    assert fields == {
        "title",
        "project_name",
        "procurement_id",
        "procurement_type",
        "purchaser",
        "agency",
        "budget_amount",
        "award_supplier",
        "award_amount",
        "announcement_date",
        "bid_deadline",
        "opening_date",
        "contact_person",
        "contact_phone",
        "source_url",
        "source_site",
        "summary",
        "content",
    }
    assert template.schema_id == schema.schema_id
    assert set(template.aliases) <= fields
    assert {
        "project_name",
        "purchaser",
        "budget_amount",
        "award_supplier",
    } <= set(template.aliases)
    TemplateService(TEMPLATES_DIR).validate_template(template, schema)


def test_procurement_catalog_records_are_seeded_active(
    procurement_catalog_client: TestClient,
) -> None:
    schemas = procurement_catalog_client.get("/api/v1/schemas")
    templates = procurement_catalog_client.get("/api/v1/templates")

    assert schemas.status_code == 200
    assert any(
        item["schema_id"] == "procurement_doc"
        and item["version"] == "1.0.0"
        and item["status"] == "active"
        and item["content_hash"].startswith("sha256:")
        for item in schemas.json()["items"]
    )
    assert templates.status_code == 200
    assert any(
        item["template_id"] == "procurement_doc_base_v1"
        and item["schema_id"] == "procurement_doc"
        and item["version"] == "1.0.0"
        and item["status"] == "active"
        and item["content_hash"].startswith("sha256:")
        for item in templates.json()["items"]
    )


def test_referenced_procurement_versions_cannot_be_archived(
    procurement_catalog_client: TestClient,
) -> None:
    doc_id = import_procurement_document(procurement_catalog_client)
    task_id = create_procurement_task(procurement_catalog_client, doc_id)
    executed = procurement_catalog_client.post(f"/api/v1/tasks/{task_id}/execute")
    assert executed.status_code == 200

    archive_schema = procurement_catalog_client.post(
        "/api/v1/schemas/procurement_doc/versions/1.0.0/archive"
    )
    archive_template = procurement_catalog_client.post(
        "/api/v1/templates/procurement_doc_base_v1/versions/1.0.0/archive"
    )

    assert archive_schema.status_code == 400
    assert archive_template.status_code == 400

    detail = procurement_catalog_client.get(f"/api/v1/tasks/{task_id}")

    assert detail.status_code == 200
    assert detail.json()["schema_version"] == "1.0.0"
    assert detail.json()["template_version"] == "1.0.0"


def test_real_world_evaluator_uses_procurement_catalog() -> None:
    source = EVAL_REAL_WORLD_UIR.read_text(encoding="utf-8")

    assert '"procurement_doc": {\n        "schema_id": "procurement_doc",' in source
    assert '"template_id": "procurement_doc_base_v1"' in source
