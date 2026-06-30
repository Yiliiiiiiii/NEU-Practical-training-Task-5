import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"


def load_script(name: str) -> ModuleType:
    path = SCRIPTS_DIR / f"{name}.py"
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def evaluation_fixture() -> dict[str, Any]:
    return {
        "items": [
            {
                "doc_id": "general-ok",
                "doc_type": "general_doc",
                "validation_passed": True,
            },
            {
                "doc_id": "policy-failed",
                "doc_type": "policy_doc",
                "validation_passed": False,
            },
        ],
        "validation_failed_cases": [
            {
                "doc_id": "policy-failed",
                "doc_type": "policy_doc",
                "stage": "validation",
                "error": "Missing required fields: issuer",
            }
        ],
    }


def mapping_fixture() -> dict[str, Any]:
    return {
        "summary": {"badcase_violation_count": 0},
        "per_document": [
            {
                "doc_id": "general-ok",
                "doc_type": "general_doc",
                "validation_passed": True,
                "required_missing": [],
                "review_evidence": [
                    {
                        "target_field_id": "source",
                        "source_field_name": "source_url",
                        "confidence": 0.62,
                        "confidence_tier": "low",
                        "review_required_reason": "Fuzzy mapping requires review.",
                        "evidence_text": ["fuzzy score 0.80 requires review"],
                    }
                ],
                "metrics": {"badcase_violation_count": 0},
            },
            {
                "doc_id": "policy-failed",
                "doc_type": "policy_doc",
                "validation_passed": False,
                "required_missing": ["issuer"],
                "review_evidence": [
                    {
                        "target_field_id": "publish_date",
                        "source_field_name": "发布日期",
                        "confidence": 0.55,
                        "confidence_tier": "low",
                        "review_required_reason": "Ambiguous date.",
                        "evidence_text": ["multiple date candidates"],
                    }
                ],
                "metrics": {"badcase_violation_count": 0},
            },
        ],
    }


def test_aggregate_validation_gaps_by_document_type() -> None:
    analyzer = load_script("analyze_real_world_validation_gaps")

    report = analyzer.analyze_reports(
        evaluation_fixture(),
        mapping_fixture(),
        package_reports=[],
    )

    assert report["summary"] == {
        "total_docs": 2,
        "strict_pass_count": 1,
        "strict_failed_count": 1,
        "badcase_violation_count": 0,
    }
    assert list(report["by_doc_type"]) == [
        "general_doc",
        "meeting_doc",
        "policy_doc",
        "procurement_doc",
    ]
    assert report["by_doc_type"]["general_doc"]["doc_count"] == 1
    assert report["by_doc_type"]["general_doc"]["strict_pass"] == 1
    assert report["by_doc_type"]["policy_doc"]["strict_failed"] == 1
    assert report["by_doc_type"]["policy_doc"]["top_missing_required_fields"] == [
        {"field": "issuer", "count": 1}
    ]
    assert report["by_doc_type"]["policy_doc"]["top_review_required_fields"] == [
        {"field": "publish_date", "count": 1}
    ]
    assert report["by_doc_type"]["policy_doc"]["top_low_confidence_sources"] == [
        {"source": "发布日期", "count": 1}
    ]
    failure = next(
        item for item in report["field_failures"] if item["target_field"] == "issuer"
    )
    assert set(failure) == {
        "doc_id",
        "doc_type",
        "target_field",
        "stage",
        "reason",
        "source_candidates",
        "evidence",
        "suggested_action",
    }
    assert failure["target_field"] == "issuer"
    review_failure = next(
        item
        for item in report["field_failures"]
        if item["target_field"] == "publish_date"
    )
    assert review_failure["stage"] == "mapping_review"
    assert review_failure["source_candidates"] == ["发布日期"]
    assert review_failure["evidence"] == ["multiple date candidates"]


def test_repeated_review_source_is_not_recommended_for_a_nonmissing_target() -> None:
    analyzer = load_script("analyze_real_world_validation_gaps")
    evaluation = {
        "items": [
            {
                "doc_id": f"policy-{index}",
                "doc_type": "policy_doc",
                "validation_passed": False,
            }
            for index in range(2)
        ]
    }
    mapping = {
        "per_document": [
            {
                "doc_id": f"policy-{index}",
                "doc_type": "policy_doc",
                "validation_passed": False,
                "required_missing": ["issuer"],
                "review_evidence": [
                    {
                        "target_field_id": "keywords",
                        "source_field_name": "extracted_block_count",
                        "confidence_tier": "low",
                    }
                ],
            }
            for index in range(2)
        ]
    }

    report = analyzer.analyze_reports(evaluation, mapping, package_reports=[])

    assert report["by_doc_type"]["policy_doc"]["recommended_template_changes"] == []


def test_analysis_is_deterministic_for_identical_inputs() -> None:
    analyzer = load_script("analyze_real_world_validation_gaps")

    first = analyzer.analyze_reports(
        evaluation_fixture(),
        mapping_fixture(),
        package_reports=[],
    )
    second = analyzer.analyze_reports(
        evaluation_fixture(),
        mapping_fixture(),
        package_reports=[],
    )

    assert first == second
    assert "generated_at" not in first


@pytest.mark.parametrize(
    ("evaluation", "mapping", "message"),
    [
        (
            {"items": "not-an-array"},
            mapping_fixture(),
            "evaluation_report.items must be an array",
        ),
        (
            {"items": ["not-an-object"]},
            mapping_fixture(),
            r"evaluation_report.items\[0\] must be an object",
        ),
        (
            {
                "items": [
                    {
                        "doc_id": "bad-type",
                        "doc_type": "invoice",
                        "validation_passed": False,
                    }
                ]
            },
            {"per_document": []},
            "unsupported doc_type",
        ),
        (
            {
                "items": [
                    {
                        "doc_id": "bad-state",
                        "doc_type": "policy_doc",
                        "validation_passed": "failed",
                    }
                ]
            },
            {"per_document": []},
            "validation_passed must be boolean",
        ),
        (
            evaluation_fixture(),
            {"per_document": "not-an-array"},
            "mapping_report.per_document must be an array",
        ),
        (
            evaluation_fixture(),
            {"per_document": [{}]},
            r"mapping_report.per_document\[0\].doc_id",
        ),
    ],
)
def test_analysis_rejects_malformed_required_report_shapes(
    evaluation: dict[str, Any],
    mapping: dict[str, Any],
    message: str,
) -> None:
    analyzer = load_script("analyze_real_world_validation_gaps")

    with pytest.raises(ValueError, match=message):
        analyzer.analyze_reports(evaluation, mapping, package_reports=[])


def test_analysis_accepts_failed_case_document_id_entries() -> None:
    analyzer = load_script("analyze_real_world_validation_gaps")
    evaluation = evaluation_fixture()
    evaluation["validation_failed_cases"] = ["policy-failed"]

    report = analyzer.analyze_reports(
        evaluation,
        mapping_fixture(),
        package_reports=[],
    )

    assert report["summary"]["strict_failed_count"] == 1


def test_summary_only_badcase_count_is_rendered_as_warning() -> None:
    analyzer = load_script("analyze_real_world_validation_gaps")
    mapping = copy.deepcopy(mapping_fixture())
    mapping["summary"]["badcase_violation_count"] = 2

    report = analyzer.analyze_reports(
        evaluation_fixture(),
        mapping,
        package_reports=[],
    )
    markdown = analyzer.render_markdown(report)

    assert report["summary"]["badcase_violation_count"] == 2
    assert report["badcase_warnings"] == [
        {
            "reported_count": 2,
            "details_available": False,
            "warning": "2 badcase violation(s) were reported without detail rows.",
        }
    ]
    assert "2 badcase violation(s) were reported without detail rows." in markdown


def test_partial_badcase_details_preserve_summary_total_and_warn_for_missing() -> None:
    analyzer = load_script("analyze_real_world_validation_gaps")
    mapping = copy.deepcopy(mapping_fixture())
    mapping["summary"]["badcase_violation_count"] = 3
    detail = {
        "doc_id": "policy-failed",
        "case_id": "badcase-1",
        "target_field": "issuer",
    }
    mapping["badcase_violations"] = [detail]

    report = analyzer.analyze_reports(
        evaluation_fixture(),
        mapping,
        package_reports=[],
    )
    markdown = analyzer.render_markdown(report)

    assert report["summary"]["badcase_violation_count"] == 3
    assert report["badcase_warnings"][0] == detail
    missing_warning = report["badcase_warnings"][1]
    assert missing_warning["missing_detail_count"] == 2
    assert missing_warning["reported_count"] == 3
    assert "2 badcase violation detail(s) are missing" in missing_warning["warning"]
    assert "2 badcase violation detail(s) are missing" in markdown


def test_badcase_details_cannot_exceed_nonzero_summary_total() -> None:
    analyzer = load_script("analyze_real_world_validation_gaps")
    mapping = copy.deepcopy(mapping_fixture())
    mapping["summary"]["badcase_violation_count"] = 1
    mapping["badcase_violations"] = [
        {"doc_id": "general-ok", "case_id": "badcase-1"},
        {"doc_id": "policy-failed", "case_id": "badcase-2"},
    ]

    with pytest.raises(ValueError, match="detail count 2 exceeds summary count 1"):
        analyzer.analyze_reports(
            evaluation_fixture(),
            mapping,
            package_reports=[],
        )


def test_cli_discovers_package_reports_and_writes_json_and_markdown(
    tmp_path: Path,
) -> None:
    reports_dir = tmp_path / "reports"
    write_json(reports_dir / "real_world_eval_report.json", evaluation_fixture())
    write_json(
        reports_dir / "real_world_mapping_eval_report.json",
        mapping_fixture(),
    )
    package_dir = reports_dir / "real_world_packages" / "policy-failed"
    write_json(
        package_dir / "validation_report.json",
        {
            "doc_id": "policy-failed",
            "doc_type": "policy_doc",
            "validation_passed": False,
            "missing_required_fields": ["issuer"],
        },
    )
    write_json(
        package_dir / "mapping_report.json",
        {
            "doc_id": "policy-failed",
            "review_required_items": [
                {
                    "target_field_id": "publish_date",
                    "source_field_name": "发布日期",
                    "confidence": 0.55,
                }
            ],
        },
    )
    package_only_dir = reports_dir / "real_world_packages" / "nested" / "package-only"
    write_json(
        package_only_dir / "validation_report.json",
        {
            "doc_id": "package-only",
            "doc_type": "meeting_doc",
            "validation_passed": False,
            "missing_required_fields": ["meeting_title"],
        },
    )
    write_json(
        package_only_dir / "mapping_report.json",
        {
            "doc_id": "package-only",
            "review_required_items": [
                {
                    "target_field_id": "meeting_date",
                    "source_field_name": "会议日期",
                    "confidence": 0.55,
                    "review_required_reason": "Ambiguous date.",
                }
            ],
        },
    )
    output_json = tmp_path / "gap.json"
    output_md = tmp_path / "gap.md"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "analyze_real_world_validation_gaps.py"),
            "--reports-dir",
            str(reports_dir),
            "--out-json",
            str(output_json),
            "--out-md",
            str(output_md),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["summary"]["strict_failed_count"] == 2
    assert payload["by_doc_type"]["meeting_doc"]["doc_count"] == 1
    assert any(
        item["doc_id"] == "package-only"
        and item["target_field"] == "meeting_title"
        for item in payload["field_failures"]
    )
    package_review = next(
        item
        for item in payload["field_failures"]
        if item["doc_id"] == "package-only"
        and item["target_field"] == "meeting_date"
    )
    assert package_review["stage"] == "mapping_review"
    assert package_review["source_candidates"] == ["会议日期"]
    markdown = output_md.read_text(encoding="utf-8")
    assert "package-only" in markdown
    for heading in (
        "## Overview",
        "## Strict Pass/Fail by Document Type",
        "## Top Failed and Review-required Fields",
        "## Recommended Aliases and Regexes",
        "## Fields That Must Stay Review-required",
        "## Badcase Warnings",
        "## Fields Not Recommended for Modification",
    ):
        assert heading in markdown


def test_cli_fails_clearly_for_malformed_required_json(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "real_world_eval_report.json").write_text("{", encoding="utf-8")
    write_json(
        reports_dir / "real_world_mapping_eval_report.json",
        mapping_fixture(),
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "analyze_real_world_validation_gaps.py"),
            "--reports-dir",
            str(reports_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Invalid JSON" in result.stderr
    assert "real_world_eval_report.json" in result.stderr


def test_cli_fails_clearly_for_malformed_required_shape(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    write_json(reports_dir / "real_world_eval_report.json", {"items": "bad"})
    write_json(
        reports_dir / "real_world_mapping_eval_report.json",
        mapping_fixture(),
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "analyze_real_world_validation_gaps.py"),
            "--reports-dir",
            str(reports_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "evaluation_report.items must be an array" in result.stderr


def test_cli_fails_clearly_for_invalid_utf8_required_json(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "real_world_eval_report.json").write_bytes(b"\xff\xfe")
    write_json(
        reports_dir / "real_world_mapping_eval_report.json",
        mapping_fixture(),
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "analyze_real_world_validation_gaps.py"),
            "--reports-dir",
            str(reports_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Unable to read JSON" in result.stderr
    assert "real_world_eval_report.json" in result.stderr
