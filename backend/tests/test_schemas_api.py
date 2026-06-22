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


@pytest.fixture
def schemas_client(tmp_path) -> Iterator[tuple[TestClient, Path]]:
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


def test_create_schema_writes_db_and_storage(schemas_client):
    client, storage_root = schemas_client
    schema = load_demo_schema()

    response = client.post("/api/v1/schemas", json={"schema": schema})

    assert response.status_code == 200
    assert response.json() == {"schema_id": "schema_general_v1", "status": "created"}
    assert (storage_root / "schemas" / "schema_general_v1" / "schema.json").is_file()


def test_list_and_get_schema_detail(schemas_client):
    client, _storage_root = schemas_client
    schema = load_demo_schema()

    client.post("/api/v1/schemas", json={"schema": schema})
    list_response = client.get("/api/v1/schemas")
    detail_response = client.get("/api/v1/schemas/schema_general_v1")

    assert list_response.status_code == 200
    assert list_response.json()["items"][0] == {
        "schema_id": "schema_general_v1",
        "name": "通用文档标准结构",
        "version": "1.0.0",
        "fields_count": 5,
    }
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["schema_id"] == "schema_general_v1"
    assert detail["fields"][0]["field_id"] == "title"
    assert detail["json_schema"]["required"] == ["title", "language"]


def test_create_schema_rejects_duplicate_field_ids(schemas_client):
    client, _storage_root = schemas_client
    schema = load_demo_schema()
    schema["fields"].append(schema["fields"][0])

    response = client.post("/api/v1/schemas", json={"schema": schema})

    assert response.status_code == 400
    assert response.json()["detail"] == "duplicate field_id: title"


def test_get_schema_returns_404_for_unknown_schema(schemas_client):
    client, _storage_root = schemas_client

    response = client.get("/api/v1/schemas/missing_schema")

    assert response.status_code == 404
    assert response.json()["detail"] == "schema not found"
