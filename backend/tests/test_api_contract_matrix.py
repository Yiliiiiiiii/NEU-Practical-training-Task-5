from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.api.v1.reports import get_mapping_service
from app.api.v1.tasks import get_conversion_service, get_package_service
from app.db.models import Base
from app.main import create_app
from app.services.storage_service import StorageService

MVP_ENDPOINTS = {
    ("post", "/api/v1/documents/import"),
    ("get", "/api/v1/documents"),
    ("get", "/api/v1/documents/{doc_id}"),
    ("post", "/api/v1/schemas"),
    ("get", "/api/v1/schemas"),
    ("get", "/api/v1/schemas/{schema_id}"),
    ("post", "/api/v1/templates"),
    ("put", "/api/v1/templates/{template_id}"),
    ("get", "/api/v1/templates"),
    ("get", "/api/v1/templates/{template_id}"),
    ("post", "/api/v1/tasks"),
    ("get", "/api/v1/tasks"),
    ("get", "/api/v1/tasks/{task_id}"),
    ("post", "/api/v1/tasks/{task_id}/replay"),
    ("post", "/api/v1/tasks/{task_id}/generate-candidates"),
    ("get", "/api/v1/tasks/{task_id}/candidates"),
    ("post", "/api/v1/tasks/{task_id}/map"),
    ("get", "/api/v1/tasks/{task_id}/mappings"),
    ("post", "/api/v1/tasks/{task_id}/mappings/review"),
    ("get", "/api/v1/tasks/{task_id}/reports/mapping"),
    ("post", "/api/v1/tasks/{task_id}/convert"),
    ("get", "/api/v1/tasks/{task_id}/canonical"),
    ("post", "/api/v1/tasks/{task_id}/package"),
    ("get", "/api/v1/tasks/{task_id}/package/download"),
    ("get", "/api/v1/tasks/{task_id}/reports/validation"),
    ("get", "/api/v1/tasks/{task_id}/reports/consistency"),
    ("get", "/api/v1/tasks/{task_id}/reports/package-verifier"),
    ("get", "/api/v1/tasks/{task_id}/trace"),
}


@pytest.fixture()
def contract_client(tmp_path) -> Iterator[tuple[TestClient, object]]:
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


def _assert_error(response, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert isinstance(response.json()["error"]["details"], list)


def test_openapi_exposes_exact_mvp_endpoint_inventory(contract_client):
    client, _ = contract_client
    schema = client.get("/openapi.json").json()
    actual = {
        (method, path)
        for path, operations in schema["paths"].items()
        if path.startswith("/api/v1")
        for method in operations
        if method in {"get", "post", "put", "patch", "delete"}
    }

    assert actual == MVP_ENDPOINTS
    assert len(actual) == 28


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("post", "/api/v1/documents/import", {}),
        ("post", "/api/v1/schemas", {}),
        ("post", "/api/v1/templates", {}),
        ("put", "/api/v1/templates/template", {}),
        ("post", "/api/v1/tasks", {}),
        (
            "post",
            "/api/v1/tasks/task/generate-candidates",
            {"include_metadata": "not-a-bool"},
        ),
        ("post", "/api/v1/tasks/task/map", {"review_threshold": "invalid"}),
        ("post", "/api/v1/tasks/task/mappings/review", {}),
        ("post", "/api/v1/tasks/task/convert", {"chunk_size": 0}),
        ("post", "/api/v1/tasks/task/package", {"package_version": 1}),
        ("post", "/api/v1/tasks/task/replay", {"options_override": []}),
    ],
)
def test_body_endpoints_reject_malformed_requests(contract_client, method, path, payload):
    client, _ = contract_client
    response = client.request(method, path, json=payload)
    _assert_error(response, 422, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/documents?page=0",
        "/api/v1/documents?page_size=101",
        "/api/v1/tasks?page=0",
        "/api/v1/tasks?page_size=101",
    ],
)
def test_list_endpoints_reject_invalid_pagination(contract_client, path):
    client, _ = contract_client
    _assert_error(client.get(path), 422, "VALIDATION_ERROR")


def test_syntactically_malformed_json_uses_validation_envelope(contract_client):
    client, _ = contract_client
    response = client.post(
        "/api/v1/tasks",
        content=b'{"doc_id":',
        headers={"content-type": "application/json"},
    )

    _assert_error(response, 422, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/v1/documents/missing", None),
        ("get", "/api/v1/schemas/missing", None),
        ("get", "/api/v1/templates/missing", None),
        ("get", "/api/v1/tasks/missing", None),
        ("post", "/api/v1/tasks/missing/generate-candidates", {}),
        ("get", "/api/v1/tasks/missing/candidates", None),
        ("post", "/api/v1/tasks/missing/map", {}),
        ("get", "/api/v1/tasks/missing/mappings", None),
        ("post", "/api/v1/tasks/missing/mappings/review", {"reviews": []}),
        ("get", "/api/v1/tasks/missing/reports/mapping", None),
        ("post", "/api/v1/tasks/missing/convert", {}),
        ("get", "/api/v1/tasks/missing/canonical", None),
        ("post", "/api/v1/tasks/missing/package", {}),
        ("get", "/api/v1/tasks/missing/package/download", None),
        ("get", "/api/v1/tasks/missing/reports/validation", None),
        ("get", "/api/v1/tasks/missing/reports/consistency", None),
        ("get", "/api/v1/tasks/missing/reports/package-verifier", None),
        ("get", "/api/v1/tasks/missing/trace", None),
    ],
)
def test_resource_endpoints_return_not_found_for_unknown_ids(
    contract_client,
    method,
    path,
    payload,
):
    client, _ = contract_client
    response = client.request(method, path, json=payload)
    _assert_error(response, 404, "NOT_FOUND")


def test_template_update_rejects_path_body_identity_mismatch(contract_client):
    client, _ = contract_client
    template = {
        "template_id": "body_id",
        "schema_id": "schema_id",
        "name": "Template",
        "version": "1.0.0",
    }

    response = client.put("/api/v1/templates/path_id", json={"template": template})

    _assert_error(response, 400, "SCHEMA_INVALID")


def test_convert_distinguishes_review_and_general_state_conflicts(contract_client):
    client, app = contract_client

    class ConversionStub:
        def __init__(self, message: str):
            self.message = message

        def convert(self, **_kwargs):
            raise ValueError(self.message)

    app.dependency_overrides[get_conversion_service] = lambda: ConversionStub(
        "task requires review before conversion"
    )
    review = client.post("/api/v1/tasks/task/convert", json={})
    _assert_error(review, 409, "MAPPING_REVIEW_REQUIRED")

    app.dependency_overrides[get_conversion_service] = lambda: ConversionStub(
        "task has invalid status"
    )
    state = client.post("/api/v1/tasks/task/convert", json={})
    _assert_error(state, 409, "TASK_STATE_ERROR")


def test_package_distinguishes_readiness_and_general_state_conflicts(contract_client):
    client, app = contract_client

    class PackageStub:
        def __init__(self, message: str):
            self.message = message

        def create_package(self, _task_id: str, _version: str):
            raise ValueError(self.message)

    app.dependency_overrides[get_package_service] = lambda: PackageStub(
        "required output is missing"
    )
    readiness = client.post("/api/v1/tasks/task/package", json={})
    _assert_error(readiness, 409, "PACKAGE_NOT_READY")

    app.dependency_overrides[get_package_service] = lambda: PackageStub(
        "task has invalid status"
    )
    state = client.post("/api/v1/tasks/task/package", json={})
    _assert_error(state, 409, "TASK_STATE_ERROR")


def test_mapping_report_maps_missing_context_to_not_found(contract_client):
    client, app = contract_client

    class MappingReportStub:
        def read_mapping_report(self, _task_id: str):
            raise LookupError("task not found")

    app.dependency_overrides[get_mapping_service] = lambda: MappingReportStub()

    response = client.get("/api/v1/tasks/task/reports/mapping")

    _assert_error(response, 404, "NOT_FOUND")


def test_mapping_report_maps_missing_file_to_not_found(contract_client):
    client, app = contract_client

    class MappingReportStub:
        def read_mapping_report(self, _task_id: str):
            raise FileNotFoundError("report file deleted")

    app.dependency_overrides[get_mapping_service] = lambda: MappingReportStub()

    response = client.get("/api/v1/tasks/task/reports/mapping")

    _assert_error(response, 404, "NOT_FOUND")
    assert response.json()["error"]["message"] == "mapping report not found"
