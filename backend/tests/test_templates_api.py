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
DEMO_SCHEMA = ROOT / "examples" / "demo" / "target_schema_general.json"
DEMO_TEMPLATE = ROOT / "examples" / "demo" / "mapping_template_general.json"


@pytest.fixture
def templates_client(tmp_path) -> Iterator[tuple[TestClient, Path]]:
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


def load_demo_schema() -> dict:
    return json.loads(DEMO_SCHEMA.read_text(encoding="utf-8"))


def load_demo_template() -> dict:
    return json.loads(DEMO_TEMPLATE.read_text(encoding="utf-8"))


def create_demo_schema(client: TestClient) -> None:
    response = client.post("/api/v1/schemas", json={"schema": load_demo_schema()})
    assert response.status_code == 200


def test_create_template_writes_db_and_storage(templates_client):
    client, storage_root = templates_client
    create_demo_schema(client)
    template = load_demo_template()

    response = client.post("/api/v1/templates", json={"template": template})

    assert response.status_code == 200
    assert response.json() == {"template_id": "tpl_general_v1", "status": "saved"}
    assert (storage_root / "templates" / "tpl_general_v1" / "template.json").is_file()


def test_list_get_and_update_template(templates_client):
    client, _storage_root = templates_client
    create_demo_schema(client)
    template = load_demo_template()
    client.post("/api/v1/templates", json={"template": template})

    list_response = client.get("/api/v1/templates")
    detail_response = client.get("/api/v1/templates/tpl_general_v1")

    assert list_response.status_code == 200
    assert list_response.json()["items"][0] == {
        "template_id": "tpl_general_v1",
        "schema_id": "schema_general_v1",
        "name": "通用文档映射模板",
        "version": "1.0.0",
        "aliases_count": 4,
        "rules_count": 3,
    }
    assert detail_response.status_code == 200
    assert detail_response.json()["aliases"]["title"][0] == "title"

    template["name"] = "通用文档映射模板 v2"
    update_response = client.put("/api/v1/templates/tpl_general_v1", json={"template": template})
    updated_detail = client.get("/api/v1/templates/tpl_general_v1")

    assert update_response.status_code == 200
    assert update_response.json() == {"template_id": "tpl_general_v1", "status": "saved"}
    assert updated_detail.json()["name"] == "通用文档映射模板 v2"


def test_create_template_rejects_unknown_schema(templates_client):
    client, _storage_root = templates_client
    template = load_demo_template()

    response = client.post("/api/v1/templates", json={"template": template})

    assert response.status_code == 404
    assert response.json()["detail"] == "schema not found"


def test_create_template_rejects_unknown_target_field(templates_client):
    client, _storage_root = templates_client
    create_demo_schema(client)
    template = load_demo_template()
    template["regex_rules"][0]["target_field_id"] = "missing_field"

    response = client.post("/api/v1/templates", json={"template": template})

    assert response.status_code == 400
    assert response.json()["detail"] == "template references unknown target field: missing_field"


def test_get_template_returns_404_for_unknown_template(templates_client):
    client, _storage_root = templates_client

    response = client.get("/api/v1/templates/missing_template")

    assert response.status_code == 404
    assert response.json()["detail"] == "template not found"
