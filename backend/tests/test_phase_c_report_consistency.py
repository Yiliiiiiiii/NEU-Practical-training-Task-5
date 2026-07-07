import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_phase_c_report_consistency.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "check_phase_c_report_consistency",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_phase_c_consistency_passes_for_aligned_reports(tmp_path: Path) -> None:
    module = load_module()
    mapping = tmp_path / "mapping.json"
    semantic = tmp_path / "semantic.json"
    strict = tmp_path / "strict.json"
    write_json(
        mapping,
        {
            "summary": {
                "dataset_size": 35,
                "strict_pass_count": 25,
                "required_missing_count": 2,
                "review_required_count": 12,
                "badcase_violation_count": 0,
            }
        },
    )
    write_json(
        semantic,
        {
            "summary": {
                "dataset_size": 35,
                "strict_pass_count": 25,
                "strict_total": 35,
                "required_missing_count": 2,
                "review_required_count": 12,
                "badcase_violations": 0,
                "llm_auto_accepted_count": 0,
            }
        },
    )
    write_json(
        strict,
        {
            "summary": {
                "package_count": 35,
                "required_missing_count": 2,
                "review_required_count": 12,
            }
        },
    )

    report = module.check_reports(
        mapping_path=mapping,
        semantic_path=semantic,
        strict_path=strict,
    )

    assert report["passed"] is True
    assert report["differences"] == []
    assert report["metrics"]["dataset_size"]["mapping"] == 35
    assert report["metrics"]["badcase_violations"]["semantic"] == 0


def test_phase_c_consistency_reports_actionable_differences(
    tmp_path: Path,
) -> None:
    module = load_module()
    mapping = tmp_path / "mapping.json"
    semantic = tmp_path / "semantic.json"
    strict = tmp_path / "strict.json"
    write_json(
        mapping,
        {
            "summary": {
                "dataset_size": 35,
                "strict_pass_count": 25,
                "required_missing_count": 2,
                "review_required_count": 12,
                "badcase_violation_count": 0,
            }
        },
    )
    write_json(
        semantic,
        {
            "summary": {
                "dataset_size": 34,
                "strict_pass_count": 24,
                "required_missing_count": 3,
                "review_required_count": 12,
                "badcase_violations": 1,
                "llm_auto_accepted_count": 0,
            }
        },
    )
    write_json(
        strict,
        {
            "summary": {
                "package_count": 35,
                "required_missing_count": 2,
                "review_required_count": 11,
            }
        },
    )

    report = module.check_reports(
        mapping_path=mapping,
        semantic_path=semantic,
        strict_path=strict,
    )

    assert report["passed"] is False
    assert {
        (item["metric"], item["reason"])
        for item in report["differences"]
    } >= {
        ("dataset_size", "value_mismatch"),
        ("required_missing_count", "value_mismatch"),
        ("badcase_violations", "semantic_safety_gate_failed"),
    }


def test_phase_c_consistency_writes_json_and_markdown(tmp_path: Path) -> None:
    module = load_module()
    mapping = tmp_path / "mapping.json"
    semantic = tmp_path / "semantic.json"
    strict = tmp_path / "strict.json"
    out = tmp_path / "consistency.json"
    markdown = tmp_path / "consistency.md"
    payload = {
        "summary": {
            "dataset_size": 1,
            "strict_pass_count": 1,
            "required_missing_count": 0,
            "review_required_count": 0,
            "badcase_violation_count": 0,
        }
    }
    write_json(mapping, payload)
    write_json(
        semantic,
        {
            "summary": {
                "dataset_size": 1,
                "strict_pass_count": 1,
                "required_missing_count": 0,
                "review_required_count": 0,
                "badcase_violations": 0,
                "llm_auto_accepted_count": 0,
            }
        },
    )
    write_json(strict, {"summary": {"package_count": 1}})

    report = module.run(
        mapping_path=mapping,
        semantic_path=semantic,
        strict_path=strict,
        out_path=out,
        markdown_path=markdown,
    )

    assert json.loads(out.read_text(encoding="utf-8"))["passed"] == report["passed"]
    assert "# Phase C Report Consistency" in markdown.read_text(encoding="utf-8")
