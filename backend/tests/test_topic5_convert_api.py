from __future__ import annotations

import copy
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db.models import Base
from app.main import create_app
from app.schemas.reports import MappingReport
from app.schemas.topic5_convert import Topic5ConvertRequest
from app.services.topic5_conversion_service import Topic5ConversionService
from tests.topic5_helpers import announcement_convert_request


@pytest.fixture
def topic5_client(tmp_path) -> Iterator[tuple[TestClient, Path]]:
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
        Settings(storage_root=str(storage_root), database_url="sqlite:///unused.db")
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
        yield client, storage_root


def test_topic5_convert_accepts_inline_config(topic5_client):
    client, _storage_root = topic5_client

    response = client.post("/api/v1/topic5/convert", json=announcement_convert_request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["schema_id"] == "announcement_doc"
    assert payload["template_id"] == "announcement_doc_base_v1"
    assert payload["content_json"]["data"]["publish_date"] == "2026-07-09"
    assert payload["content_json"]["data"]["title"]
    assert payload["content_json"]["data"]["issuer"]
    assert payload["content_json"]["data"]["body"]
    assert payload["content_markdown"].startswith("# ")
    assert payload["chunks"]
    assert payload["mapping_report"]["summary"]["input_mode"] == "inline_topic5_config"
    assert payload["mapping_report"]["summary"]["mapping_input_name"] == "mapping_template"
    assert payload["mapping_report"]["summary"]["review_required_count"] == 0
    assert payload["mapping_report"]["summary"]["required_unmapped_count"] == 0
    assert payload["content_organization_report"]["summary"]["chunk_count"] > 0
    assert payload["manifest"] is None
    assert payload["package_zip_path"] is None


def test_topic5_convert_package_creates_verified_package(topic5_client):
    client, _storage_root = topic5_client

    response = client.post("/api/v1/topic5/convert/package", json=announcement_convert_request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["package_metadata"]["schema_id"] == "announcement_doc"
    assert payload["package_zip_path"]
    assert Path(payload["package_zip_path"]).is_file()
    assert payload["package_metadata"]["status"] == "completed"
    assert payload["verifier_report"]["passed"] is True


def test_topic5_convert_accepts_preferred_mapping_rules(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["mapping_rules"] = payload.pop("mapping_template")

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["mapping_report"]["summary"]["mapping_input_name"] == "mapping_rules"


def test_topic5_request_accepts_legacy_mapping_template():
    request = Topic5ConvertRequest.model_validate(announcement_convert_request())

    assert request.mapping_input_name == "mapping_template"
    assert request.effective_mapping_template.schema_id == "announcement_doc"


def test_topic5_request_rejects_missing_mapping_rules():
    payload = announcement_convert_request()
    payload.pop("mapping_template", None)
    payload.pop("mapping_rules", None)

    with pytest.raises(ValidationError):
        Topic5ConvertRequest.model_validate(payload)


def test_topic5_request_rejects_conflicting_mapping_inputs():
    payload = announcement_convert_request()
    payload["mapping_rules"] = copy.deepcopy(payload["mapping_template"])
    payload["mapping_template"]["schema_id"] = "other_schema"

    with pytest.raises(ValidationError):
        Topic5ConvertRequest.model_validate(payload)


def test_topic5_convert_review_required_when_required_field_unmapped(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["target_schema"]["fields"].append(
        {
            "field_id": "audience",
            "name": "audience",
            "display_name": "audience",
            "type": "string",
            "required": True,
            "aliases": ["audience"],
            "constraints": {},
        }
    )

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "review_required"
    assert body["mapping_report"]["summary"]["required_unmapped_count"] >= 1


def test_topic5_convert_review_required_when_validation_fails(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["target_schema"]["fields"][0]["type"] = "date"

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "review_required"
    assert body["validation_report"]["passed"] is False


def test_topic5_final_status_failed_when_package_verifier_fails():
    report = MappingReport(
        task_id="task",
        schema_id="announcement_doc",
        summary={},
        mappings=[],
        unmapped=[],
        review_required_items=[],
    )

    status = Topic5ConversionService._final_status(
        mapping_report=report,
        validation_passed=True,
        verifier_passed=False,
        create_package=True,
    )

    assert status == "failed"
