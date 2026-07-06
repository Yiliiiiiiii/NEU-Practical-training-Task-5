import importlib.util
import json
from pathlib import Path

from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetSchema
from app.schemas.uir import UIRDocument

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_LIKE_DIR = ROOT / "examples" / "production_like"
EVAL_SCRIPT = ROOT / "scripts" / "eval_production_like.py"


def load_eval_module():
    spec = importlib.util.spec_from_file_location("eval_production_like", EVAL_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_production_like_fixtures_exist_and_parse():
    domains = {
        "policy_doc",
        "procurement_doc",
        "contract_doc",
        "meeting_doc",
        "general_doc",
    }
    schemas = {
        path.stem: TargetSchema.model_validate(read_json(path))
        for path in sorted((PRODUCTION_LIKE_DIR / "schemas").glob("*.json"))
    }
    templates = {
        path.stem: MappingTemplate.model_validate(read_json(path))
        for path in sorted((PRODUCTION_LIKE_DIR / "mapping_templates").glob("*.json"))
    }
    uir_files = sorted((PRODUCTION_LIKE_DIR / "uir").glob("*/*.json"))
    uirs = [UIRDocument.model_validate(read_json(path)) for path in uir_files]

    assert set(schemas) == {
        "policy_doc_v1",
        "procurement_doc_v1",
        "contract_doc_v1",
        "meeting_doc_v1",
        "general_doc_v1",
    }
    assert set(templates) == {
        "policy_doc_base_v1",
        "procurement_doc_base_v1",
        "contract_doc_base_v1",
        "meeting_doc_base_v1",
        "general_doc_base_v1",
    }
    assert {schema.schema_id for schema in schemas.values()} == domains
    assert {template.schema_id for template in templates.values()} == domains
    assert len(uirs) >= 14
    assert all(uir.blocks for uir in uirs)
    assert all("domain" in uir.metadata for uir in uirs)


def test_production_like_expectations_cover_each_domain():
    gold_cases = read_jsonl(PRODUCTION_LIKE_DIR / "expected" / "mapping_gold_cases.jsonl")
    badcases = read_jsonl(PRODUCTION_LIKE_DIR / "expected" / "badcases.jsonl")
    domains = {"policy_doc", "contract_doc", "meeting_doc", "general_doc"}

    assert len(gold_cases) >= 20
    assert len(badcases) >= 8
    for domain in domains:
        assert sum(case["domain"] == domain for case in gold_cases) >= 5
        assert sum(case["domain"] == domain for case in badcases) >= 2
    assert any(
        case["expected_behavior"] == "review_required_before_pack_auto_after_pack"
        for case in gold_cases
    )


def test_production_like_eval_generates_reports_and_pack_delta(tmp_path):
    eval_module = load_eval_module()

    result = eval_module.run_evaluation(
        dataset_dir=PRODUCTION_LIKE_DIR,
        output_dir=tmp_path,
    )

    json_report = tmp_path / "production_like_eval_report.json"
    markdown_report = tmp_path / "production_like_eval_report.md"
    assert json_report.is_file()
    assert markdown_report.is_file()

    report = read_json(json_report)
    assert result["summary"]["total_cases"] == report["summary"]["total_cases"]
    assert report["summary"]["total_cases"] >= 14
    assert report["phase_a"]["packs_activated"] == 0
    assert report["phase_b"]["packs_created"] == 1
    assert report["phase_b"]["packs_activated"] == 1
    assert report["phase_b"]["effective_template_pack_resolution_count"] >= 1
    assert report["phase_b"]["review_required_rate"] < report["phase_a"]["review_required_rate"]
    assert report["draft_pending_pack_effective"] is False
    assert report["old_run_snapshot_unchanged"] is True
    assert report["phase_b"]["badcase_violation_count"] == 0
    assert report["phase_b"]["gold_case_pass_rate"] == 1.0
    assert report["phase_b"]["badcase_pass_rate"] == 1.0
    assert report["downstream_smoke_summary"]["package_count"] == report[
        "content_organization_summary"
    ]["package_count"]
    assert report["downstream_smoke_summary"]["failed_count"] == 0
    assert report["service_layer_mode"] == "production_services"
    assert report["knowledge_layer_mode"] == "review_knowledge_services"
    assert all(
        "does not contain production mapping_service" not in issue
        and "simulated by evaluator active aliases" not in issue
        for issue in report["remaining_issues"]
    )
    assert all(
        "authentication" not in issue.lower()
        and "audit logging" not in issue.lower()
        for issue in report["remaining_issues"]
    )
    assert any(
        "optional offline upstream scripts" in boundary
        for boundary in report["boundaries"]
    )
    assert "Production-like Evaluation Report" in markdown_report.read_text(encoding="utf-8")
