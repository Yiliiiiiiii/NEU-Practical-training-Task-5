import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_acceptance_report.py"

EXPECTED_HEADINGS = [
    "1. 项目定位",
    "2. 课题 5 要求对应关系",
    "3. 当前实现能力总览",
    "4. 核心链路说明",
    "5. API 与前端能力说明",
    "6. 生产类评测结果",
    "7. 真实 UIR 评测结果",
    "8. 标准成果包结构",
    "9. 下游消费验证",
    "10. badcase 与人审知识闭环",
    "11. LLM fallback 安全姿态",
    "12. 项目边界与未实现事项",
    "13. 复现命令",
    "14. 当前结论",
]


def load_report_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_acceptance_report", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_optional_reports_are_recorded_without_crashing(tmp_path: Path) -> None:
    report_module = load_report_module()

    report = report_module.build_acceptance_report(tmp_path)

    production_check = report["checks"]["production_like_eval"]
    assert production_check["status"] == "missing"
    assert production_check["reason"] == "report file not found"
    assert production_check["report_path"] == "reports/production_like_eval_report.json"
    assert production_check["recommended_command"] == "python scripts/eval_production_like.py"
    assert production_check["summary"] == {}


def test_minimal_production_report_generates_json_and_markdown_outputs(
    tmp_path: Path,
) -> None:
    report_module = load_report_module()
    source_path = tmp_path / "reports" / "production_like_eval_report.json"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        json.dumps(
            {
                "summary": {"total_cases": 15},
                "phase_b": {
                    "gold_case_pass_rate": 1.0,
                    "badcase_pass_rate": 1.0,
                },
                "downstream_smoke_summary": {"failed_count": 0},
            }
        ),
        encoding="utf-8",
    )

    report = report_module.build_acceptance_report(tmp_path)
    report_module.write_reports(tmp_path, report)

    json_path = tmp_path / "reports" / "acceptance_report.json"
    report_markdown_path = tmp_path / "reports" / "acceptance_report.md"
    docs_markdown_path = tmp_path / "docs" / "acceptance_report.md"
    assert json_path.is_file()
    assert report_markdown_path.is_file()
    assert docs_markdown_path.is_file()

    saved_report = json.loads(json_path.read_text(encoding="utf-8"))
    assert "checks" in saved_report
    assert "boundaries" in saved_report
    markdown = report_markdown_path.read_text(encoding="utf-8")
    assert "课题 5" in markdown
    assert "UIR -> Schema -> Mapping" in markdown
    assert all(f"## {heading}" in markdown for heading in EXPECTED_HEADINGS)
    assert docs_markdown_path.read_text(encoding="utf-8") == markdown


def test_malformed_optional_report_is_recorded_and_generation_continues(
    tmp_path: Path,
) -> None:
    report_module = load_report_module()
    source_path = tmp_path / "reports" / "production_like_eval_report.json"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("{not-json", encoding="utf-8")

    report = report_module.build_acceptance_report(tmp_path)
    report_module.write_reports(tmp_path, report)

    production_check = report["checks"]["production_like_eval"]
    assert production_check["status"] == "error"
    assert production_check["reason"].startswith("invalid JSON:")
    assert production_check["summary"] == {}
    assert (tmp_path / "reports" / "acceptance_report.json").is_file()


def test_source_evidence_is_reduced_to_core_summaries(tmp_path: Path) -> None:
    report_module = load_report_module()
    source_path = tmp_path / "reports" / "real_world_eval_report.json"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        json.dumps(
            {
                "dataset_size": 1,
                "import_pass_count": 1,
                "task_execute_pass_count": 1,
                "package_verify_pass_count": 1,
                "validation_failed_cases": [],
                "items": [{"doc_id": "detail-that-should-not-be-copied"}],
            }
        ),
        encoding="utf-8",
    )

    report = report_module.build_acceptance_report(tmp_path)

    assert "items" not in report["evidence"]["real_world_eval"]["summary"]
    assert report["evidence"]["real_world_eval"]["summary"]["dataset_size"] == 1


def test_current_handoff_verification_markers_are_recognized(tmp_path: Path) -> None:
    report_module = load_report_module()
    handoff_path = tmp_path / "docs" / "final_handoff_status.md"
    handoff_path.parent.mkdir(parents=True)
    handoff_path.write_text(
        "\n".join(
            [
                "# SchemaPack Agent Final Handoff Status",
                "- Backend pytest: 203 passed.",
                "- Ruff: clean.",
                "- Frontend production build: successful.",
                "- OpenAPI export: 32 paths written to `docs/openapi.json`.",
            ]
        ),
        encoding="utf-8",
    )

    report = report_module.build_acceptance_report(tmp_path)

    assert report["checks"]["pytest"]["status"] == "passed"
    assert report["checks"]["frontend_build"]["status"] == "passed"


def test_json_report_path_cannot_escape_repository_root(tmp_path: Path) -> None:
    report_module = load_report_module()
    outside_path = tmp_path.parent / "outside-acceptance-evidence.json"
    outside_path.write_text('{"status": "passed"}', encoding="utf-8")

    evidence = report_module.read_json_report(
        tmp_path,
        f"../{outside_path.name}",
        "python unsafe.py",
    )

    assert evidence["status"] == "error"
    assert evidence["reason"] == "report path escapes repository root"
    assert evidence["summary"] == {}


def test_guideline_delivery_artifacts_exist_with_json_and_markdown_pairs() -> None:
    required_files = [
        "examples/production_like/schemas/procurement_doc_v1.json",
        "examples/production_like/mapping_templates/procurement_doc_base_v1.json",
        "examples/production_like/expected/procurement_mapping_gold_cases.jsonl",
        "examples/real_world/review_fixtures/procurement_review_decisions.jsonl",
        "examples/real_world/retrieval_queries.jsonl",
        "scripts/eval_real_world_knowledge_loop.py",
        "scripts/eval_chunk_retrieval.py",
        "scripts/eval_llm_fallback_modes.py",
        "frontend/src/evidence.ts",
        "frontend/src/components/MappingEvidencePanel.tsx",
        "frontend/src/components/ValidationIssuePanel.tsx",
        "frontend/src/components/ChunkEvidencePanel.tsx",
        "frontend/src/components/PackageManifestPanel.tsx",
        "frontend/src/components/KnowledgeComparisonPanel.tsx",
    ]
    report_pairs = [
        "reports/acceptance_report",
        "reports/real_world_knowledge_loop_report",
        "reports/chunk_retrieval_eval_report",
        "reports/llm_fallback_eval_report",
    ]

    missing = [path for path in required_files if not (ROOT / path).is_file()]
    assert missing == []
    for stem in report_pairs:
        assert (ROOT / f"{stem}.json").is_file()
        assert (ROOT / f"{stem}.md").is_file()
