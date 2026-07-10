from __future__ import annotations

from typing import Any

import pytest

from app.schemas.conversion_assertions import ConversionAssertionConfig


def make_config(assertions: list[dict[str, Any]]) -> ConversionAssertionConfig:
    return ConversionAssertionConfig.model_validate(
        {
            "contract_version": "1.0",
            "schema_id": "announcement_doc",
            "assertion_set_version": "1.0.0",
            "defaults": {"severity": "error", "missing_optional_field": "skip"},
            "assertions": assertions,
        }
    )


def definition(
    assertion_id: str,
    path: str,
    operator: str,
    *,
    parameters: dict[str, Any] | None = None,
    severity: str = "error",
    optional: bool = False,
) -> dict[str, Any]:
    return {
        "assertion_id": assertion_id,
        "path": path,
        "operator": operator,
        "parameters": parameters or {},
        "severity": severity,
        "optional": optional,
        "message": f"{assertion_id} failed",
    }


def evaluate(content: dict[str, Any], assertions: list[dict[str, Any]], mapping_report=None):
    from app.services.conversion_assertion_service import ConversionAssertionService

    return ConversionAssertionService().evaluate(
        task_id="task-assert",
        schema_pack_id="announcement_doc",
        schema_pack_version="1.0.0",
        schema_id="announcement_doc",
        content_json=content,
        assertion_config=make_config(assertions),
        mapping_report=mapping_report,
    )


@pytest.mark.parametrize(
    ("operator", "value", "parameters", "content"),
    [
        ("exists", "value", {}, {"data": {"field": "value"}}),
        ("non_empty", "value", {}, {"data": {"field": "value"}}),
        ("type_is", "value", {"expected": "string"}, {"data": {"field": "value"}}),
        ("date_format", "2026-07-10", {"formats": ["%Y-%m-%d"]}, None),
        (
            "datetime_format",
            "2026-07-10 12:30",
            {"formats": ["%Y-%m-%d %H:%M"]},
            None,
        ),
        (
            "regex_match",
            "AB-123456",
            {"pattern": r"^[A-Z]{2}-\d{6}$", "mode": "fullmatch"},
            None,
        ),
        ("enum_allowed", "published", {"values": ["draft", "published"]}, None),
        (
            "number_range",
            10,
            {"min": 0, "max": 10, "inclusive_min": True, "inclusive_max": True},
            None,
        ),
        ("text_length", "abcdefghij", {"min": 10, "max": 20}, None),
        ("array_length", [1, 2], {"min": 1, "max": 3}, None),
        ("url_like", "https://example.com/a", {}, None),
        (
            "equal_to_path",
            "doc-1",
            {"other_path": "$.metadata.document_id"},
            {"data": {"field": "doc-1"}, "metadata": {"document_id": "doc-1"}},
        ),
        (
            "not_equal_to_path",
            "2026-07-10",
            {"other_path": "$.metadata.retrieved_at"},
            {
                "data": {"field": "2026-07-10"},
                "metadata": {"retrieved_at": "2026-07-11"},
            },
        ),
    ],
)
def test_required_assertion_operators_pass(
    operator: str,
    value: Any,
    parameters: dict[str, Any],
    content: dict[str, Any] | None,
) -> None:
    payload = content or {"data": {"field": value}}

    report = evaluate(
        payload,
        [definition(operator, "$.data.field", operator, parameters=parameters)],
    )

    assert report.passed is True
    assert report.passed_count == 1
    assert report.error_count == 0
    assert report.results[0].status == "passed"


def test_warning_failure_does_not_fail_report() -> None:
    report = evaluate(
        {"data": {"title": "  "}},
        [definition("title_non_empty", "$.data.title", "non_empty", severity="warning")],
    )

    assert report.passed is True
    assert report.warning_count == 1
    assert report.error_count == 0
    assert report.results[0].status == "failed"


def test_error_failure_fails_report_and_optional_missing_is_skipped() -> None:
    report = evaluate(
        {"data": {"title": ""}},
        [
            definition("title_non_empty", "$.data.title", "non_empty"),
            definition(
                "optional_url",
                "$.metadata.source_url",
                "url_like",
                optional=True,
            ),
        ],
    )

    assert report.passed is False
    assert report.error_count == 1
    assert report.skipped_count == 1
    assert [item.status for item in report.results] == ["failed", "skipped"]


def test_optional_cross_path_assertion_skips_when_other_path_is_missing() -> None:
    report = evaluate(
        {"data": {"publish_date": "2026-07-10"}, "metadata": {}},
        [
            definition(
                "dates_must_differ",
                "$.data.publish_date",
                "not_equal_to_path",
                parameters={"other_path": "$.metadata.retrieved_at"},
                optional=True,
            )
        ],
    )

    assert report.passed is True
    assert report.skipped_count == 1
    assert report.failed_count == 0


def test_issue_includes_mapping_evidence_and_bounded_preview() -> None:
    report = evaluate(
        {"data": {"publish_date": "x" * 250}},
        [
            definition(
                "publish_date_iso",
                "$.data.publish_date",
                "date_format",
                parameters={"formats": ["%Y-%m-%d"]},
            )
        ],
        mapping_report={
            "mappings": [
                {
                    "target_field_id": "publish_date",
                    "source_path": "$.blocks[2].text",
                    "candidate_id": "cand-date",
                    "method": "global_assignment",
                }
            ]
        },
    )

    issue = report.issues[0]
    assert issue.source_path == "$.blocks[2].text"
    assert issue.source_candidate_id == "cand-date"
    assert issue.mapping_method == "global_assignment"
    assert issue.actual_preview == "x" * 200


def test_issue_order_is_deterministic_by_severity_id_and_path() -> None:
    report = evaluate(
        {"data": {"a": "", "b": ""}},
        [
            definition("z_warning", "$.data.b", "non_empty", severity="warning"),
            definition("b_error", "$.data.b", "non_empty"),
            definition("a_error", "$.data.a", "non_empty"),
        ],
    )

    assert [item.assertion_id for item in report.issues] == [
        "a_error",
        "b_error",
        "z_warning",
    ]
