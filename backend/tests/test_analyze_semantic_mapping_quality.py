import importlib.util
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analyze_semantic_mapping_quality.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "analyze_semantic_mapping_quality",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_package(
    path: Path,
    *,
    doc_id: str,
    schema_id: str,
    mappings: list[dict] | None = None,
    reviews: list[dict] | None = None,
    unmapped: list[dict] | None = None,
    validation_issues: list[dict] | None = None,
) -> None:
    mappings = mappings or []
    reviews = reviews or []
    unmapped = unmapped or []
    validation_issues = validation_issues or []
    mapping_report = {
        "summary": {
            "review_required_count": len(reviews),
            "required_unmapped_count": sum(
                1 for item in unmapped if item.get("required")
            ),
        },
        "mappings": mappings,
        "review_required_items": reviews,
        "unmapped": unmapped,
    }
    validation_report = {
        "passed": not any(
            issue.get("level", "error") == "error" for issue in validation_issues
        ),
        "issues": validation_issues,
    }
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "metadata.json",
            json.dumps(
                {
                    "doc_id": doc_id,
                    "schema_id": schema_id,
                    "template_id": f"{schema_id}_base_v1",
                },
                ensure_ascii=False,
            ),
        )
        archive.writestr(
            "mapping_report.json",
            json.dumps(mapping_report, ensure_ascii=False),
        )
        archive.writestr(
            "validation_report.json",
            json.dumps(validation_report, ensure_ascii=False),
        )
        archive.writestr(
            "transform_report.json",
            json.dumps({"errors": validation_issues}, ensure_ascii=False),
        )


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_analyzer_classifies_missing_transform_and_unsafe_gaps(tmp_path: Path) -> None:
    module = load_module()
    packages = tmp_path / "packages"
    packages.mkdir()
    write_package(
        packages / "missing.zip",
        doc_id="general-missing",
        schema_id="general_doc",
        unmapped=[
            {
                "target_field_id": "service_object",
                "required": False,
                "reason": "source evidence produced no candidate",
            }
        ],
    )
    write_package(
        packages / "transform.zip",
        doc_id="policy-transform",
        schema_id="policy_doc",
        mappings=[
            {
                "source_field": {
                    "source_name": "发布日期",
                    "source_path": "$.blocks.b1.text",
                },
                "target_field_id": "publish_date",
                "status": "accepted",
                "value_sample": "2025年13月1日",
                "source_blocks": ["b1"],
            }
        ],
        validation_issues=[
            {
                "field_id": "publish_date",
                "level": "error",
                "code": "date_format_invalid",
                "failure_type": "date_format_invalid",
                "message": "日期格式不符合 ISO",
            }
        ],
    )
    write_package(
        packages / "unsafe.zip",
        doc_id="policy-unsafe",
        schema_id="policy_doc",
        mappings=[
            {
                "source_field": {
                    "source_name": "成文日期",
                    "source_path": "$.blocks.b2.text",
                },
                "target_field_id": "publish_date",
                "status": "accepted",
                "value_sample": "2025-06-01",
                "source_blocks": ["b2"],
            }
        ],
    )
    gold = tmp_path / "gold.jsonl"
    write_jsonl(
        gold,
        [
            {
                "doc_id": "general-missing",
                "doc_type": "general_doc",
                "expected_mappings": [
                    {
                        "source_name": "服务对象",
                        "source_path": "blocks[1].text",
                        "target_field": "service_object",
                    }
                ],
                "expected_review_required": [],
            },
            {
                "doc_id": "policy-transform",
                "doc_type": "policy_doc",
                "expected_mappings": [
                    {
                        "source_name": "发布日期",
                        "source_path": "blocks[1].text",
                        "target_field": "publish_date",
                    }
                ],
                "expected_review_required": [],
            },
            {
                "doc_id": "policy-unsafe",
                "doc_type": "policy_doc",
                "expected_mappings": [],
                "expected_review_required": [
                    {
                        "source_name": "成文日期",
                        "source_path": "blocks[2].text",
                        "target_field": "publish_date",
                    }
                ],
            },
        ],
    )
    badcases = tmp_path / "badcases.jsonl"
    write_jsonl(
        badcases,
        [
            {
                "case_id": "issue-date-is-not-publication-date",
                "doc_id": "policy-unsafe",
                "forbidden_auto_mapping": {
                    "source_name": "成文日期",
                    "target_field": "publish_date",
                },
                "severity": "high",
            }
        ],
    )

    report = module.run(
        packages_root=packages,
        gold_path=gold,
        badcases_path=badcases,
    )

    assert report["summary"]["dataset_size"] == 3
    assert report["summary"]["badcase_violations"] == 1
    assert report["gaps_by_gap_type"]["candidate_not_extracted"] == 1
    assert report["gaps_by_gap_type"]["transform_invalid"] == 1
    assert report["gaps_by_gap_type"]["unsafe_ambiguous"] == 1
    assert report["strict_validation_failures"][0]["target_field"] == "publish_date"
    assert report["unsafe_candidates"][0]["source_name"] == "成文日期"
    assert all(
        item["gap_type"] != "unsafe_ambiguous" for item in report["ranked_fixes"]
    )


def test_analyzer_writes_required_markdown_sections(tmp_path: Path) -> None:
    module = load_module()
    packages = tmp_path / "packages"
    packages.mkdir()
    write_package(
        packages / "general.zip",
        doc_id="general-1",
        schema_id="general_doc",
    )
    gold = tmp_path / "gold.jsonl"
    write_jsonl(
        gold,
        [
            {
                "doc_id": "general-1",
                "doc_type": "general_doc",
                "expected_mappings": [],
                "expected_review_required": [],
            }
        ],
    )
    badcases = tmp_path / "badcases.jsonl"
    write_jsonl(badcases, [])
    output = tmp_path / "semantic.json"
    markdown = tmp_path / "semantic.md"

    report = module.run(
        packages_root=packages,
        gold_path=gold,
        badcases_path=badcases,
        out_path=output,
        markdown_path=markdown,
    )

    assert json.loads(output.read_text(encoding="utf-8"))["summary"] == report["summary"]
    text = markdown.read_text(encoding="utf-8")
    for heading in (
        "## 总体指标",
        "## 按文档类型",
        "## 按目标字段",
        "## Ranked Fixes",
        "## Unsafe Candidates",
        "## Strict Validation Failures",
        "## 禁止自动修复项",
        "## 下一步建议",
    ):
        assert heading in text
