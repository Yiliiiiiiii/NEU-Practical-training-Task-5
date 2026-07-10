from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "schema_packs" / "examples"


def test_schema_pack_contract_evaluator_passes_positive_and_badcase_fixtures() -> None:
    from scripts.eval_schema_pack_contracts import evaluate_all

    report = evaluate_all(EXAMPLES, verify_package=True)

    assert report["status"] == "passed"
    assert report["total_schema_packs"] == 2
    assert report["passed_schema_packs"] == 2
    assert [item["schema_pack_id"] for item in report["items"]] == [
        "announcement_doc",
        "event_notice_doc",
    ]
    assert all(item["positive_examples_passed"] == 1 for item in report["items"])
    assert all(item["badcases_passed"] == 1 for item in report["items"])
    assert all(item["package_verifier_passed"] is True for item in report["items"])
    assert any(
        item["package_with_assertion_report_verified"] is True
        for item in report["items"]
    )
    assert any(
        item["package_without_assertion_report_verified"] is True
        for item in report["items"]
    )


def test_schema_pack_contract_evaluator_fails_missing_expected_badcase(tmp_path) -> None:
    from scripts.eval_schema_pack_contracts import evaluate_pack

    pack_dir = tmp_path / "examples" / "announcement_doc"
    shutil.copytree(EXAMPLES / "announcement_doc", pack_dir)
    expected_path = pack_dir / "badcases" / "badcase_001_expected_assertions.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    expected["expected_failed_assertion_ids"] = ["not_produced"]
    expected_path.write_text(json.dumps(expected), encoding="utf-8")

    item = evaluate_pack(pack_dir, verify_package=False)

    assert item["status"] == "failed"
    assert item["badcases_passed"] == 0
    assert "badcases/badcase_001_uir.json:not_produced" in item["unexpected_assertion_failures"]


def test_schema_pack_contract_evaluator_fails_badcase_severity_mismatch(tmp_path) -> None:
    from scripts.eval_schema_pack_contracts import evaluate_pack

    pack_dir = tmp_path / "examples" / "announcement_doc"
    shutil.copytree(EXAMPLES / "announcement_doc", pack_dir)
    expected_path = pack_dir / "badcases" / "badcase_001_expected_assertions.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    expected["expected_severities"] = {"dates_must_differ": "error"}
    expected_path.write_text(json.dumps(expected), encoding="utf-8")

    item = evaluate_pack(pack_dir, verify_package=False)

    assert item["status"] == "failed"
    assert item["badcases_passed"] == 0
    assert (
        "badcases/badcase_001_uir.json:dates_must_differ:"
        "expected_severity=error:actual_severity=warning"
        in item["unexpected_assertion_failures"]
    )


def test_schema_pack_contract_evaluator_rejects_missing_badcase_fixtures(
    tmp_path,
) -> None:
    from scripts.eval_schema_pack_contracts import evaluate_pack

    pack_dir = tmp_path / "examples" / "announcement_doc"
    shutil.copytree(EXAMPLES / "announcement_doc", pack_dir)
    for path in (pack_dir / "badcases").glob("badcase_*.json"):
        path.unlink()

    item = evaluate_pack(pack_dir, verify_package=False)

    assert item["status"] == "failed"
    assert item["badcases_total"] == 0
    assert "badcases:no_badcase_fixtures" in item["unexpected_assertion_failures"]


def test_schema_pack_contract_evaluator_all_mode_has_stable_order() -> None:
    from scripts.eval_schema_pack_contracts import evaluate_all

    first = evaluate_all(EXAMPLES, verify_package=False)
    second = evaluate_all(EXAMPLES, verify_package=False)

    assert [item["schema_pack_id"] for item in first["items"]] == [
        item["schema_pack_id"] for item in second["items"]
    ]
