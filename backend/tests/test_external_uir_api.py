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
FIXTURES = ROOT / "examples" / "external_uir"


@pytest.fixture
def external_uir_client(tmp_path) -> Iterator[tuple[TestClient, Path]]:
    from app.api.deps import get_db, get_settings, get_storage_service
    from app.services.storage_service import StorageService

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    storage_root = tmp_path / "storage"
    settings = Settings(storage_root=str(storage_root), database_url="sqlite:///unused.db")
    app = create_app(settings)

    def override_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_storage_service] = lambda: StorageService(storage_root)

    with TestClient(app) as client:
        yield client, storage_root


def read_fixture(relative_path: str) -> dict:
    return json.loads((FIXTURES / relative_path).read_text(encoding="utf-8"))


def test_list_adapters_returns_builtin_capabilities(external_uir_client):
    client, _storage_root = external_uir_client

    response = client.get("/api/v1/external-uir/adapters")

    assert response.status_code == 200
    body = response.json()
    assert [item["adapter_id"] for item in body["items"]] == ["block_list", "section_tree"]
    assert body["items"][0]["supported_dialects"] == ["block-list", "block_list"]
    assert body["items"][0]["requires_llm"] is False


def test_detect_external_uir_selects_adapter_without_converting(external_uir_client):
    client, _storage_root = external_uir_client
    payload = read_fixture("dialect_b_section_tree/sample_meeting_external.json")

    response = client.post(
        "/api/v1/external-uir/detect",
        json={"payload": payload, "source_system": "topic11", "dialect_hint": "auto"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_adapter"]["adapter_id"] == "section_tree"
    assert body["selected_adapter"]["confidence"] >= 0.9
    assert body["review_required"] is False
    assert "standard_uir" not in body


def test_detect_unknown_external_uir_requires_review(external_uir_client):
    client, _storage_root = external_uir_client

    response = client.post(
        "/api/v1/external-uir/detect",
        json={"payload": {"unexpected": []}, "source_system": "topic11"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_adapter"] is None
    assert body["review_required"] is True
    assert body["error"] == "unsupported_dialect"


def test_convert_block_list_returns_uir_and_route_report(external_uir_client):
    client, _storage_root = external_uir_client
    payload = read_fixture("dialect_a_block_list/sample_procurement_external.json")

    response = client.post(
        "/api/v1/external-uir/convert",
        json={
            "payload": payload,
            "source_system": "topic11",
            "dialect_hint": "auto",
            "route_schema": True,
            "allow_llm": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["standard_uir"]["doc_id"]
    assert body["adapter_report"]["status"] in {"passed", "review_required"}
    assert body["adapter_report"]["llm_auto_accepted_count"] == 0
    assert body["route_report"]["selected_schema_id"] == "procurement_doc"
    assert body["route_report"]["selected_template_id"] == "procurement_doc_base_v1"


def test_convert_section_tree_returns_uir(external_uir_client):
    client, _storage_root = external_uir_client
    payload = read_fixture("dialect_b_section_tree/sample_meeting_external.json")

    response = client.post(
        "/api/v1/external-uir/convert",
        json={"payload": payload, "source_system": "topic11"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["standard_uir"]["source"]["source_type"] == "external_uir"
    assert body["route_report"]["selected_schema_id"] == "meeting_doc"


def test_import_creates_document_but_not_task(external_uir_client):
    client, storage_root = external_uir_client
    payload = read_fixture("dialect_a_block_list/sample_policy_external.json")

    response = client.post(
        "/api/v1/external-uir/import",
        json={"payload": payload, "source_system": "topic11"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["doc_id"] == body["document"]["doc_id"]
    assert (storage_root / "documents" / body["doc_id"] / "uir.json").is_file()
    task_list = client.get("/api/v1/tasks")
    assert task_list.status_code == 200
    assert task_list.json()["total"] == 0


def test_create_task_uses_imported_document_and_does_not_execute(external_uir_client):
    client, _storage_root = external_uir_client
    payload = read_fixture("dialect_a_block_list/sample_procurement_external.json")
    imported = client.post(
        "/api/v1/external-uir/import",
        json={"payload": payload, "source_system": "topic11"},
    ).json()

    response = client.post(
        "/api/v1/external-uir/create-task",
        json={
            "doc_id": imported["doc_id"],
            "schema_id": "procurement_doc",
            "template_id": "procurement_doc_base_v1",
            "schema_version": "1.0.0",
            "template_version": "1.0.0",
            "route_report": imported["route_report"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"].startswith("task_")
    task = client.get(f"/api/v1/tasks/{body['task_id']}").json()
    assert task["status"] == "created"
    assert task["package_zip_path"] is None


def test_allow_llm_disabled_returns_warning_and_deterministic_result(external_uir_client):
    client, _storage_root = external_uir_client
    payload = read_fixture("dialect_a_block_list/sample_procurement_external.json")

    response = client.post(
        "/api/v1/external-uir/convert",
        json={
            "payload": payload,
            "source_system": "topic11",
            "allow_llm": True,
            "llm_mode": "deepseek",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "DeepSeek assistance is disabled" in body["warnings"][0]
    assert body["adapter_report"]["llm_used"] is False
    assert body["adapter_report"]["assisted_suggestions"] == []


def test_convert_unknown_dialect_returns_400(external_uir_client):
    client, _storage_root = external_uir_client

    response = client.post(
        "/api/v1/external-uir/convert",
        json={"payload": {"unexpected": []}, "source_system": "topic11"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "unsupported external UIR dialect"


def test_convert_binds_adapter_hint_to_router_evidence(external_uir_client):
    client, _storage_root = external_uir_client

    response = client.post(
        "/api/v1/external-uir/convert",
        json={
            "payload": {
                "id": "hinted_001",
                "title": "Plain document",
                "schema_hint": "meeting_doc",
                "chunks": [{"id": "c1", "type": "paragraph", "text": "Plain text"}],
            },
            "source_system": "topic11",
        },
    )

    assert response.status_code == 200
    route = response.json()["route_report"]
    meeting = next(
        item for item in route["candidates"] if item["schema_id"] == "meeting_doc"
    )
    assert any(item["evidence_type"] == "adapter_hint" for item in meeting["evidence"])
    assert route["selected_schema_id"] is None
    assert route["review_required"] is True
