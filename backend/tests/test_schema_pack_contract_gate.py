from __future__ import annotations

import json


def contract_report(*, status: str = "passed") -> dict:
    item_status = "passed" if status == "passed" else "failed"
    return {
        "status": status,
        "items": [
            {
                "schema_pack_id": "announcement_doc",
                "status": item_status,
                "contract_valid": status == "passed",
                "positive_examples_passed": 1 if status == "passed" else 0,
                "positive_examples_total": 1,
                "badcases_passed": 1 if status == "passed" else 0,
                "badcases_total": 1,
                "unexpected_assertion_failures": (
                    []
                    if status == "passed"
                    else ["badcases/badcase_001_uir.json:dates_must_differ"]
                ),
                "package_verifier_passed": status == "passed",
                "package_with_assertion_report_verified": status == "passed",
                "package_without_assertion_report_verified": status == "passed",
            }
        ],
    }


def test_phase3_gate_report_passes_without_quality_score_or_route() -> None:
    from scripts.check_schema_pack_contract_gate import build_gate_report

    report = build_gate_report(
        contract_report(),
        {"status": "passed", "warnings": []},
        {"status": "passed", "warnings": []},
    )

    assert report["status"] == "passed"
    assert report["failed_checks"] == []
    serialized = json.dumps(report)
    assert "quality_score" not in serialized
    assert "quality_grade" not in serialized
    assert "route_recommendation" not in serialized


def test_phase3_gate_report_references_exact_failing_pack_and_fixture() -> None:
    from scripts.check_schema_pack_contract_gate import build_gate_report

    report = build_gate_report(
        contract_report(status="failed"),
        {"status": "passed", "warnings": []},
        {"status": "passed", "warnings": []},
    )

    assert report["status"] == "failed"
    assert (
        "announcement_doc:badcases/badcase_001_uir.json:dates_must_differ"
        in report["failed_checks"]
    )


def test_phase3_gate_rejects_empty_fixture_sets() -> None:
    from scripts.check_schema_pack_contract_gate import build_gate_report

    contract = contract_report()
    contract["items"][0]["positive_examples_passed"] = 0
    contract["items"][0]["positive_examples_total"] = 0
    contract["items"][0]["badcases_passed"] = 0
    contract["items"][0]["badcases_total"] = 0

    report = build_gate_report(
        contract,
        {"status": "passed", "warnings": []},
        {"status": "passed", "warnings": []},
    )

    assert report["checks"]["positive_examples"] == "failed"
    assert report["checks"]["badcase_detection"] == "failed"
    assert report["status"] == "failed"


def test_phase3_gate_requires_verified_packages_with_and_without_assertion_report() -> None:
    from scripts.check_schema_pack_contract_gate import build_gate_report

    contract = contract_report()
    contract["items"][0]["package_with_assertion_report_verified"] = False

    report = build_gate_report(
        contract,
        {"status": "passed", "warnings": []},
        {"status": "passed", "warnings": []},
    )

    assert report["checks"]["package_1_1_compatibility"] == "failed"
    assert report["status"] == "failed"


def test_phase3_gate_exit_is_nonzero_only_when_fail_on_gate_enabled() -> None:
    from scripts.check_schema_pack_contract_gate import gate_exit_code

    failed = {"status": "failed"}

    assert gate_exit_code(failed, fail_on_gate=False) == 0
    assert gate_exit_code(failed, fail_on_gate=True) == 1


def test_phase3_gate_always_writes_json_and_markdown_reports(tmp_path) -> None:
    from scripts.check_schema_pack_contract_gate import write_reports

    report = {
        "status": "failed",
        "checks": {"manifest_contracts": "failed"},
        "failed_checks": ["manifest_contracts"],
        "warnings": [],
    }
    json_path = tmp_path / "gate.json"
    markdown_path = tmp_path / "gate.md"

    write_reports(report, json_path, markdown_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))["status"] == "failed"
    assert "manifest_contracts" in markdown_path.read_text(encoding="utf-8")
