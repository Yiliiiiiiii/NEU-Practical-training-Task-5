from __future__ import annotations

import json
from pathlib import Path

from app.schemas.topic5_convert import Topic5ConvertRequest
from app.services.topic5_conversion_service import Topic5ConversionService

ROOT = Path(__file__).resolve().parents[2]
REQUEST_PATH = ROOT / "examples" / "topic5_inline" / "announcement_convert_request.json"


def request_payload(assertion: dict | None = None, *, options: dict | None = None) -> dict:
    payload = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
    payload.pop("output_assertions", None)
    if assertion is not None:
        payload["output_assertions"] = {
            "contract_version": "1.0",
            "schema_id": "announcement_doc",
            "assertion_set_version": "1.0.0",
            "assertions": [assertion],
        }
    payload["options"].update(options or {})
    return payload


def regex_assertion(*, severity: str = "error") -> dict:
    return {
        "assertion_id": "title_pattern",
        "path": "$.data.title",
        "operator": "regex_match",
        "severity": severity,
        "parameters": {"pattern": "^never-match$", "mode": "fullmatch"},
        "message": "Title must match the configured pattern.",
    }


def convert(tmp_path: Path, payload: dict, *, create_package: bool = False):
    request = Topic5ConvertRequest.model_validate(payload)
    return Topic5ConversionService(tmp_path).convert(
        request,
        create_package=create_package,
    )


def test_conversion_without_assertions_remains_compatible(tmp_path) -> None:
    response = convert(tmp_path, request_payload())

    assert response.status == "completed"
    assert response.conversion_assertion_report is None


def test_conversion_with_passing_assertion_completes(tmp_path) -> None:
    response = convert(
        tmp_path,
        request_payload(
            {
                "assertion_id": "title_non_empty",
                "path": "$.data.title",
                "operator": "non_empty",
            }
        ),
    )

    assert response.status == "completed"
    assert response.conversion_assertion_report["passed"] is True


def test_warning_only_assertion_keeps_conversion_completed(tmp_path) -> None:
    response = convert(tmp_path, request_payload(regex_assertion(severity="warning")))

    assert response.status == "completed"
    assert response.conversion_assertion_report["warning_count"] == 1


def test_error_assertion_requires_review_by_default(tmp_path) -> None:
    response = convert(tmp_path, request_payload(regex_assertion()))

    assert response.status == "review_required"
    assert response.conversion_assertion_report["error_count"] == 1


def test_strict_error_assertion_fails_conversion(tmp_path) -> None:
    response = convert(
        tmp_path,
        request_payload(
            regex_assertion(),
            options={"strict_output_assertions": True},
        ),
    )

    assert response.status == "failed"


def test_assertion_issue_contains_mapping_evidence(tmp_path) -> None:
    response = convert(tmp_path, request_payload(regex_assertion()))

    issue = response.conversion_assertion_report["issues"][0]
    assert issue["source_path"]
    assert issue["source_candidate_id"]
    assert issue["mapping_method"]


def test_optional_assertion_report_is_listed_in_package_manifest(tmp_path) -> None:
    response = convert(
        tmp_path,
        request_payload(
            {
                "assertion_id": "title_non_empty",
                "path": "$.data.title",
                "operator": "non_empty",
            },
            options={"include_assertion_report_in_package": True},
        ),
        create_package=True,
    )

    report_entry = next(
        item
        for item in response.manifest["files"]
        if item["path"] == "reports/conversion_assertion_report.json"
    )
    assert report_entry["required"] is False
    assert report_entry["role"] == "conversion_assertion_report"
    assert response.verifier_report["passed"] is True
