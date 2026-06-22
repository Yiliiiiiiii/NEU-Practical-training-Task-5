import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.api.v1.tasks import get_task_service
from app.db.models import Base
from app.main import create_app
from app.services.storage_service import StorageService

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "demo"


def _load(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.fixture()
def error_client(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    storage = StorageService(tmp_path / "storage")
    app = create_app(init_database=False)

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[deps.get_db] = override_db
    app.dependency_overrides[deps.get_storage_service] = lambda: storage
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, app


def assert_error(response, status: int, code: str):
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)
    assert isinstance(body["error"]["details"], list)


def test_request_validation_uses_unified_error(error_client):
    client, _ = error_client

    response = client.post("/api/v1/tasks", json={})

    assert_error(response, 422, "VALIDATION_ERROR")
    assert {item["path"] for item in response.json()["error"]["details"]} >= {
        "body.doc_id",
        "body.schema_id",
        "body.template_id",
    }


def test_missing_resource_uses_unified_error(error_client):
    client, _ = error_client

    response = client.get("/api/v1/tasks/missing_task")

    assert_error(response, 404, "NOT_FOUND")


def test_schema_validation_uses_schema_invalid_code(error_client):
    client, _ = error_client
    schema = _load("target_schema_general.json")
    schema["fields"].append(dict(schema["fields"][0]))

    response = client.post("/api/v1/schemas", json={"schema": schema})

    assert_error(response, 400, "SCHEMA_INVALID")


def test_task_state_and_package_readiness_have_specific_codes(error_client):
    client, _ = error_client
    uir = _load("example_uir_general_doc.json")
    assert client.post("/api/v1/documents/import", json={"uir": uir}).status_code == 200
    task = client.post(
        "/api/v1/tasks",
        json={
            "doc_id": uir["doc_id"],
            "schema_id": "schema_missing",
            "template_id": "template_missing",
        },
    ).json()

    convert = client.post(
        f"/api/v1/tasks/{task['task_id']}/convert",
        json={"render_outputs": True, "chunk_size": 500},
    )
    package = client.post(f"/api/v1/tasks/{task['task_id']}/package", json={})

    assert_error(convert, 409, "TASK_STATE_ERROR")
    assert_error(package, 409, "PACKAGE_NOT_READY")


def test_unexpected_exception_hides_internal_details(error_client):
    client, app = error_client

    class FailingTaskService:
        def get_task(self, task_id: str):
            raise RuntimeError(f"secret database detail for {task_id}")

    app.dependency_overrides[get_task_service] = lambda: FailingTaskService()
    response = client.get("/api/v1/tasks/task_secret")

    assert_error(response, 500, "INTERNAL_ERROR")
    assert response.json()["error"]["message"] == "Internal server error"
    assert "secret" not in response.text
