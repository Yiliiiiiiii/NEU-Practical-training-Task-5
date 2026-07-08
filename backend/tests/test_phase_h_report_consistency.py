import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_phase_h_report_consistency.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "build_phase_h_report_consistency",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_phase_h_consistency_uses_explicit_doc_and_field_counts(tmp_path: Path) -> None:
    module = load_module()
    reports_root = tmp_path / "reports"
    write_json(
        reports_root / "phase_g_non_procurement_mapping_eval_report.json",
        {
            "summary": {
                "dataset_size": 2,
                "average_recall": 0.75,
                "strict_pass_count": 1,
                "required_missing_count": 1,
                "review_required_count": 2,
                "badcase_violation_count": 0,
                "llm_auto_accepted_count": 0,
                "package_verify_pass_count": 2,
            },
            "documents": [
                {"doc_id": "doc-a", "required_missing": ["issuer"], "review_evidence": []},
                {
                    "doc_id": "doc-b",
                    "required_missing": [],
                    "review_evidence": [{"target_field_id": "x"}],
                },
            ],
        },
    )
    write_json(
        reports_root / "phase_g_semantic_mapping_quality_report.json",
        {
            "summary": {
                "dataset_size": 2,
                "average_recall": 0.70,
                "strict_pass_count": 1,
                "strict_total": 2,
                "required_missing_count": 3,
                "review_required_count": 4,
                "badcase_violations": 0,
                "llm_auto_accepted_count": 0,
            },
            "documents": [
                {"doc_id": "doc-a", "review_required_count": 2},
                {"doc_id": "doc-b", "review_required_count": 0},
            ],
        },
    )
    write_json(
        reports_root / "phase_g_strict_validation_failure_analysis.json",
        {
            "summary": {
                "package_count": 2,
                "validation_pass_count": 1,
                "required_missing_count": 3,
                "review_required_count": 4,
            },
            "items": [
                {
                    "doc_id": "doc-a",
                    "required_missing": ["issuer", "publish_date"],
                    "review_required_count": 3,
                },
                {
                    "doc_id": "doc-b",
                    "required_missing": ["meeting_date"],
                    "review_required_count": 1,
                },
            ],
        },
    )

    report = module.build_report(reports_root)

    assert report["status"] == "passed"
    assert "missing" not in report["unified_metrics"]
    assert "required_missing_doc_count" in report["metric_definitions"]
    assert "required_missing_field_count" in report["metric_definitions"]
    semantic = report["reports"]["semantic_mapping_quality"]
    assert semantic["required_missing_field_count"] == 3
    strict = report["reports"]["strict_validation_failure_analysis"]
    assert strict["required_missing_doc_count"] == 2
    assert strict["required_missing_field_count"] == 3
    assert report["safety"]["badcase_violations"] == 0
    assert report["safety"]["llm_auto_accepted_count"] == 0


def test_phase_h_consistency_writes_json_and_markdown(tmp_path: Path) -> None:
    module = load_module()
    reports_root = tmp_path / "reports"
    payload = {
        "summary": {
            "dataset_size": 1,
            "average_recall": 1.0,
            "strict_pass_count": 1,
            "required_missing_count": 0,
            "review_required_count": 0,
            "badcase_violations": 0,
            "llm_auto_accepted_count": 0,
        },
        "documents": [{"doc_id": "doc", "required_missing": [], "review_required_count": 0}],
    }
    for name in (
        "phase_g_non_procurement_mapping_eval_report.json",
        "phase_g_semantic_mapping_quality_report.json",
        "phase_g_strict_validation_failure_analysis.json",
    ):
        write_json(reports_root / name, payload)
    out = tmp_path / "out.json"
    markdown = tmp_path / "out.md"

    report = module.run(reports_root=reports_root, out_path=out, markdown_path=markdown)

    assert json.loads(out.read_text(encoding="utf-8"))["status"] == report["status"]
    text = markdown.read_text(encoding="utf-8")
    assert "# Phase H Report Consistency" in text
    assert "required_missing_doc_count" in text
    assert "required_missing_field_count" in text
