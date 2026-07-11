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
from app.schemas.topic5_convert import Topic5ConvertRequest
from app.services.package_verifier_service import PackageVerifierService
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
    assert payload["content_markdown"].startswith(
        '<!-- topic5:document:start doc_id="uir_announcement_001"'
    )
    assert payload["artifact_consistency_report"]["passed"] is True
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


def test_topic5_document_summary_is_shared_across_json_markdown_and_report(
    topic5_client,
):
    client, _storage_root = topic5_client

    response = client.post("/api/v1/topic5/convert", json=announcement_convert_request())

    assert response.status_code == 200
    body = response.json()
    summary = body["document_summary"]
    assert summary["text"]
    assert summary["faithfulness_passed"] is True
    assert summary["source_block_ids"]
    assert summary["source_chunk_ids"]
    assert body["content_json"]["document_summary"] == summary
    assert body["content_organization_report"]["document_summary"] == summary
    assert (
        f"<!-- topic5:summary:start -->\n{summary['text']}\n"
        "<!-- topic5:summary:end -->"
    ) in body["content_markdown"]


def test_topic5_document_summary_can_be_disabled(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["content_organization"]["summary"] = {
        "chunk_mode": "deterministic",
        "document_mode": "none",
        "document_max_sentences": 5,
        "document_max_chars": 500,
    }

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["document_summary"] is None
    assert body["content_json"]["document_summary"] is None
    assert (
        "<!-- topic5:summary:start -->\n\n<!-- topic5:summary:end -->"
        in body["content_markdown"]
    )
    assert body["artifact_consistency_report"]["summary_consistent"] is True


def test_topic5_document_summary_is_deterministic_across_three_runs(topic5_client):
    client, _storage_root = topic5_client

    summaries = [
        client.post("/api/v1/topic5/convert", json=announcement_convert_request())
        .json()["document_summary"]
        for _index in range(3)
    ]

    assert summaries[0] == summaries[1] == summaries[2]


def test_topic5_inline_passes_upstream_entity_to_only_relevant_chunk(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["uir"]["entities"] = [
        {
            "mention": "信息化办公室",
            "canonical_name": "信息化办公室",
            "entity_type": "organization",
            "normalized_id": "org:it-office",
            "link_status": "linked",
            "confidence": 1.0,
            "source_block_ids": ["b2"],
            "source_agent": "topic7",
            "evidence": {"source": "upstream"},
        }
    ]

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 200
    chunks = response.json()["chunks"]
    relevant = [chunk for chunk in chunks if "b2" in chunk["source_block_ids"]]
    unrelated = [chunk for chunk in chunks if "b2" not in chunk["source_block_ids"]]
    assert relevant
    assert relevant[0]["entity_tags"][0]["normalized_id"] == "org:it-office"
    assert relevant[0]["entity_tags"][0]["source"] == "upstream"
    assert all(chunk["entity_tags"] == [] for chunk in unrelated)


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
    assert metadata["document_summary"] == body["document_summary"]
    assert "document_summary_v1" in metadata["features"]
    assert "artifact_consistency_v1" in metadata["features"]
    consistency_report = json.loads(
        (package_dir / "artifact_consistency_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert consistency_report == body["artifact_consistency_report"]
    assert consistency_report["passed"] is True
    assert "metadata_template_report.json" in {
        item["path"] for item in body["manifest"]["files"]
    }
    manifested = {item["path"] for item in body["manifest"]["files"]}
    assert "artifact_consistency_report.json" in manifested
    assert "verifier_report.json" in manifested


def test_package_verifier_rejects_missing_declared_consistency_report(
    topic5_client,
):
    client, _storage_root = topic5_client
    response = client.post(
        "/api/v1/topic5/convert/package", json=announcement_convert_request()
    )
    package_dir = Path(response.json()["package_zip_path"]).parent
    (package_dir / "artifact_consistency_report.json").unlink()

    report = PackageVerifierService().verify_package(package_dir)

    assert report.passed is False
    assert any(
        issue.path == "artifact_consistency_report.json"
        and issue.code == "required_file_missing"
        for issue in report.errors
    )


def test_package_verifier_rejects_failed_consistency_report(topic5_client):
    client, _storage_root = topic5_client
    response = client.post(
        "/api/v1/topic5/convert/package", json=announcement_convert_request()
    )
    package_dir = Path(response.json()["package_zip_path"]).parent
    report_path = package_dir / "artifact_consistency_report.json"
    consistency = json.loads(report_path.read_text(encoding="utf-8"))
    consistency["passed"] = False
    report_path.write_text(json.dumps(consistency), encoding="utf-8")

    report = PackageVerifierService().verify_package(package_dir)

    assert report.passed is False
    assert any(issue.code == "artifact_consistency_failed" for issue in report.errors)


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


def test_topic5_inline_uses_internal_chunk_provider_by_default(topic5_client):
    client, _storage_root = topic5_client

    response = client.post("/api/v1/topic5/convert", json=announcement_convert_request())

    assert response.status_code == 200
    trace = response.json()["content_organization_report"]["provider_trace"]
    assert trace["requested_provider"] == "internal"
    assert trace["used_provider"] == "internal"
    assert trace["external_requested"] is False
    assert trace["fallback_used"] is False


def test_topic5_inline_topic11_missing_endpoint_falls_back(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["content_organization"]["provider"] = "topic11"
    payload["content_organization"]["fallback_to_internal"] = True

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 200
    trace = response.json()["content_organization_report"]["provider_trace"]
    assert trace["requested_provider"] == "topic11"
    assert trace["used_provider"] == "internal"
    assert trace["fallback_used"] is True
    assert trace["fallback_reason"] == "topic11_endpoint_missing"


def test_topic5_inline_strict_topic11_missing_endpoint_is_422(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["content_organization"]["provider"] = "topic11"
    payload["content_organization"]["strict_provider"] = True

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == "topic11_endpoint_missing"


def test_topic11_api_key_is_not_written_to_package(
    topic5_client, monkeypatch: pytest.MonkeyPatch
):
    client, _storage_root = topic5_client
    secret = "topic11-package-secret"
    monkeypatch.setenv("TOPIC11_API_KEY", secret)
    payload = announcement_convert_request()
    payload["content_organization"]["provider"] = "topic11"
    payload["content_organization"]["fallback_to_internal"] = True

    response = client.post("/api/v1/topic5/convert/package", json=payload)

    assert response.status_code == 200
    package_dir = Path(response.json()["package_zip_path"]).parent
    serialized = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in package_dir.rglob("*")
        if path.is_file() and path.suffix != ".zip"
    )
    assert secret not in serialized


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


def test_topic5_convert_source_absent_unmapped_reviews_for_schema_validation(
    topic5_client,
):
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
    audience = next(
        item
        for item in body["mapping_report"]["unmapped"]
        if item["target_field_id"] == "audience"
    )
    assert audience["source_present"] is False
    assert body["validation_report"]["passed"] is False


def test_topic5_convert_review_required_when_validation_fails(topic5_client):
    client, _storage_root = topic5_client
    payload = announcement_convert_request()
    payload["target_schema"]["fields"][0]["type"] = "date"

    response = client.post("/api/v1/topic5/convert", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "review_required"
    assert body["validation_report"]["passed"] is False


def test_topic5_package_verifier_failure_overrides_artifact_consistency_failure(
    topic5_client,
    monkeypatch,
):
    from app.services.artifact_consistency_service import ArtifactConsistencyService

    client, _storage_root = topic5_client
    original_verify = ArtifactConsistencyService.verify

    def fail_consistency(self, **kwargs):
        report = original_verify(self, **kwargs)
        return report.model_copy(update={"passed": False})

    monkeypatch.setattr(ArtifactConsistencyService, "verify", fail_consistency)

    response = client.post(
        "/api/v1/topic5/convert/package",
        json=announcement_convert_request(),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["artifact_consistency_report"]["passed"] is False
    assert payload["verifier_report"]["passed"] is False
    assert payload["status"] == "failed"
