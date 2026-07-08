import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analyze_phase_h_mapping_gaps.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "analyze_phase_h_mapping_gaps",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase_h_gap_drilldown_normalizes_semantic_quality_gaps() -> None:
    module = load_module()
    semantic_report = {
        "summary": {"dataset_size": 2},
        "gaps_by_doc_type": {"policy_doc": 2},
        "gaps_by_target_field": {"publish_date": 2},
        "gaps_by_gap_type": {"candidate_not_extracted": 2},
        "ranked_fixes": [
            {
                "rank": 1,
                "doc_type": "policy_doc",
                "target_field": "publish_date",
                "gap_type": "candidate_not_extracted",
                "count": 2,
                "recommended_action": "enhance_candidate_extraction",
                "risk": "low",
            }
        ],
        "documents": [
            {
                "doc_id": "doc-a",
                "doc_type": "policy_doc",
                "mapping_recall": 0.5,
                "strict_passed": False,
                "review_required_count": 0,
            },
            {
                "doc_id": "doc-b",
                "doc_type": "policy_doc",
                "mapping_recall": 0.4,
                "strict_passed": False,
                "review_required_count": 1,
            },
        ],
    }

    drilldown = module.build_drilldown(semantic_report, top_n=30)

    assert drilldown["summary"]["dataset_size"] == 2
    assert drilldown["summary"]["gap_count"] == 2
    assert drilldown["summary"]["by_doc_type"] == {"policy_doc": 2}
    assert drilldown["summary"]["by_target_field"] == {"publish_date": 2}
    assert drilldown["summary"]["top_ranked_fixes"][0]["target_field"] == "publish_date"
    assert drilldown["items"][0] == {
        "doc_id": "doc-a",
        "doc_type": "policy_doc",
        "target_field": "publish_date",
        "gap_type": "candidate_not_extracted",
        "gold_value_shape": "date",
        "current_decision": None,
        "candidate_present": False,
        "source_anchor_present": False,
        "risk": "low",
        "recommended_action": "enhance_candidate_extraction",
        "notes": "mapping_recall=0.5000; strict_passed=False; review_required_count=0",
    }


def test_phase_h_gap_drilldown_writes_json_and_markdown(tmp_path: Path) -> None:
    module = load_module()
    source = tmp_path / "semantic.json"
    out = tmp_path / "gap.json"
    markdown = tmp_path / "gap.md"
    source.write_text(
        json.dumps(
            {
                "summary": {"dataset_size": 1},
                "gaps_by_doc_type": {"policy_doc": 1},
                "gaps_by_target_field": {"issuer": 1},
                "gaps_by_gap_type": {"candidate_extracted_but_not_ranked": 1},
                "ranked_fixes": [
                    {
                        "rank": 1,
                        "doc_type": "policy_doc",
                        "target_field": "issuer",
                        "gap_type": "candidate_extracted_but_not_ranked",
                        "count": 1,
                        "recommended_action": "improve_evidence_ranking",
                        "risk": "medium",
                    }
                ],
                "documents": [{"doc_id": "doc", "doc_type": "policy_doc"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = module.run(source_report=source, out_path=out, markdown_path=markdown)

    assert json.loads(out.read_text(encoding="utf-8"))["summary"] == report["summary"]
    text = markdown.read_text(encoding="utf-8")
    assert "# Phase H Mapping Gap Drilldown" in text
    assert "policy_doc.issuer" in text
