from __future__ import annotations

import copy
import json
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
from app.services.package_verifier_service import PackageVerifierService
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


def test_topic5_metadata_template_controls_response_and_content_json(topic5_client):
    client, _storage_root = topic5_client

    response = client.post("/api/v1/topic5/convert", json=announcement_convert_request())

    assert response.status_code == 200
    body = response.json()
    assert body["document_metadata"] == {"language": "zh-CN", "source": "example"}
    assert body["content_json"]["document_metadata"] == body["document_metadata"]
    assert body["content_json"]["metadata_template"] == {
        "template_id": "announcement_doc_base_v1",
        "version": "1.0.0",
    }
    assert body["metadata_template_report"]["passed"] is True
    assert body["metadata_template_report"]["field_traces"]


def test_topic5_same_uir_with_two_templates_changes_document_metadata(topic5_client):
    client, _storage_root = topic5_client
    first = announcement_convert_request()
    first["metadata_template"]["metadata_fields"].append(
        {"field_id": "classification", "type": "string", "default": "internal"}
    )
    second = copy.deepcopy(first)
    second["metadata_template"]["metadata_fields"][-1]["default"] = "public"

    first_response = client.post("/api/v1/topic5/convert", json=first)
    second_response = client.post("/api/v1/topic5/convert", json=second)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["document_metadata"]["classification"] == "internal"
    assert second_response.json()["document_metadata"]["classification"] == "public"


def test_topic5_required_metadata_missing_is_review_required_and_localized(
    topic5_client,
):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["metadata_template"]["metadata_fields"].append(
        {"field_id": "classification", "type": "string", "required": True}
    )

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "review_required"
    issue = body["metadata_template_report"]["issues"][0]
    assert issue["stage"] == "metadata_template"
    assert issue["path"] == "document_metadata.classification"
    assert issue["error_code"] == "metadata_required_missing"
    assert "classification" not in body["document_metadata"]
    validation_issue = next(
        item
        for item in body["validation_report"]["issues"]
        if item["code"] == "metadata_required_missing"
    )
    assert validation_issue["stage"] == "metadata_template"
    assert validation_issue["path"] == "document_metadata.classification"
    assert body["content_organization_report"]["document_quality_flags"] == [
        {
            "tag": "validation_error",
            "rule_id": "quality:validation_error",
            "scope": "document",
            "evidence": "Required document metadata field is missing.",
            "source_block_ids": [],
            "related_field_ids": ["classification"],
            "related_issue_codes": ["metadata_required_missing"],
        }
    ]
    assert all(
        "validation_error" not in chunk["quality_tags"] for chunk in body["chunks"]
    )


def test_topic5_strict_required_metadata_missing_fails(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["metadata_template"]["metadata_fields"].append(
        {"field_id": "classification", "type": "string", "required": True}
    )
    payload["options"]["strict_metadata_template"] = True

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "failed"


def test_topic5_metadata_type_mismatch_is_review_required_and_localized(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["metadata_template"]["metadata_fields"][1]["type"] = "integer"

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "review_required"
    issue = body["metadata_template_report"]["issues"][0]
    assert issue["path"] == "document_metadata.language"
    assert issue["error_code"] == "metadata_type_mismatch"


def test_topic5_legacy_request_without_metadata_template_remains_valid(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload.pop("metadata_template")

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["document_metadata"] == {}
    assert body["metadata_template_report"] is None
    assert body["content_json"]["document_metadata"] == {}


def test_topic5_package_contains_metadata_template_artifact_and_feature(topic5_client):
    client, _storage_root = topic5_client

    response = client.post(
        "/api/v1/topic5/convert/package", json=announcement_convert_request()
    )

    assert response.status_code == 200
    body = response.json()
    package_dir = Path(body["package_zip_path"]).parent
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    report = json.loads(
        (package_dir / "metadata_template_report.json").read_text(encoding="utf-8")
    )
    assert metadata["document_metadata"] == body["document_metadata"]
    assert metadata["metadata_template"]["template_id"] == (
        "announcement_doc_base_v1"
    )
    assert "metadata_template_v1" in metadata["features"]
    assert report["passed"] is True
    assert "metadata_template_report.json" in {
        item["path"] for item in body["manifest"]["files"]
    }


def test_package_verifier_rejects_missing_declared_metadata_report(topic5_client):
    client, _storage_root = topic5_client
    response = client.post(
        "/api/v1/topic5/convert/package", json=announcement_convert_request()
    )
    package_dir = Path(response.json()["package_zip_path"]).parent
    (package_dir / "metadata_template_report.json").unlink()

    report = PackageVerifierService().verify_package(package_dir)

    assert report.passed is False
    assert any(
        issue.path == "metadata_template_report.json"
        and issue.code == "required_file_missing"
        for issue in report.errors
    )


def test_package_verifier_rejects_unmanifested_declared_metadata_report(
    topic5_client,
):
    client, _storage_root = topic5_client
    response = client.post(
        "/api/v1/topic5/convert/package", json=announcement_convert_request()
    )
    package_dir = Path(response.json()["package_zip_path"]).parent
    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = [
        item
        for item in manifest["files"]
        if item["path"] != "metadata_template_report.json"
    ]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = PackageVerifierService().verify_package(package_dir)

    assert report.passed is False
    assert any(
        issue.path == "metadata_template_report.json"
        and issue.code == "required_file_not_manifested"
        for issue in report.errors
    )


def test_package_verifier_rejects_invalid_declared_metadata_report(topic5_client):
    client, _storage_root = topic5_client
    response = client.post(
        "/api/v1/topic5/convert/package", json=announcement_convert_request()
    )
    package_dir = Path(response.json()["package_zip_path"]).parent
    (package_dir / "metadata_template_report.json").write_text("{}", encoding="utf-8")

    report = PackageVerifierService().verify_package(package_dir)

    assert report.passed is False
    assert any(
        issue.path == "metadata_template_report.json"
        and issue.code == "metadata_template_report_invalid"
        for issue in report.errors
    )


def test_topic5_convert_accepts_preferred_mapping_rules(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["mapping_rules"] = payload.pop("mapping_template")

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["mapping_report"]["summary"]["mapping_input_name"] == "mapping_rules"


def test_topic5_inline_content_tag_rules_require_no_backend_edit(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["content_organization"]["tag_rules"] = {
        "content": {
            "base_tags": ["announcement"],
            "rules": [
                {
                    "rule_id": "inline-maintenance",
                    "tag": "maintenance",
                    "any_terms": ["维护"],
                }
            ],
        },
        "management": {
            "static_tags": ["domain:campus"],
            "metadata_rules": [
                {
                    "rule_id": "inline-language",
                    "tag_template": "language:{value}",
                    "source_path": "document_metadata.language",
                }
            ],
        },
        "quality": {"enabled_builtin_rules": ["source_linked", "anchor_linked"]},
    }

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 200
    chunks = response.json()["chunks"]
    assert any("maintenance" in chunk["content_tags"] for chunk in chunks)
    assert all(
        chunk["management_tags"] == ["domain:campus", "language:zh-CN"]
        for chunk in chunks
    )
    assert all(
        not any(
            tag.startswith(("task:", "doc:", "chunk_index:"))
            for tag in chunk["management_tags"]
        )
        for chunk in chunks
    )


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


def test_topic5_request_rejects_metadata_template_schema_mismatch(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["metadata_template"]["schema_id"] = "other_doc"

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 422


def test_topic5_request_rejects_unsafe_metadata_source_path(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["metadata_template"]["metadata_fields"][0]["source_path"] = (
        "environment.API_KEY"
    )

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 422


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
