import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import eval_lineage_graph  # noqa: E402

from tests.test_lineage_graph_service import build_graph  # noqa: E402


def write_graph(tasks_root: Path, payload: dict, task_id: str = "task_1") -> Path:
    path = tasks_root / task_id / "lineage_graph.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def test_eval_lineage_graph_outputs_json_and_markdown(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    write_graph(tasks_root, build_graph().model_dump(mode="json"))
    out = tmp_path / "lineage.json"
    markdown = tmp_path / "lineage.md"

    report = eval_lineage_graph.run(
        tasks_root=tasks_root,
        out_path=out,
        markdown_path=markdown,
    )

    assert report["lineage_graph_count"] == 1
    assert report["lineage_parse_pass_count"] == 1
    assert report["lineage_parse_pass_rate"] == 1.0
    assert json.loads(out.read_text(encoding="utf-8"))["status"] == "passed"
    assert "SchemaPack-Lineage Evaluation" in markdown.read_text(encoding="utf-8")


def test_eval_detects_broken_edges(tmp_path: Path) -> None:
    payload = build_graph().model_dump(mode="json")
    payload["edges"].append(
        {
            "edge_id": "broken",
            "source_node_id": "missing",
            "target_node_id": payload["nodes"][0]["node_id"],
            "edge_type": "derived_from",
            "evidence_ids": [],
            "metadata": {},
        }
    )
    write_graph(tmp_path, payload)

    report = eval_lineage_graph.run(tasks_root=tmp_path)

    assert report["broken_edge_count"] == 1
    assert report["status"] == "failed"


def test_eval_detects_orphan_nodes(tmp_path: Path) -> None:
    payload = build_graph().model_dump(mode="json")
    payload["nodes"].append(
        {
            "node_id": "lineage:uir_block:orphan",
            "node_type": "uir_block",
            "label": "orphan",
            "status": "informational",
            "block_id": "orphan",
            "risk_flags": [],
            "metadata": {},
        }
    )
    write_graph(tmp_path, payload)

    report = eval_lineage_graph.run(tasks_root=tmp_path)

    assert report["orphan_node_count"] >= 1


def test_eval_detects_secret_like_values(tmp_path: Path) -> None:
    payload = build_graph().model_dump(mode="json")
    payload["nodes"][0]["metadata"]["api_key"] = "sk-evaluator-secret"
    write_graph(tmp_path, payload)

    report = eval_lineage_graph.run(tasks_root=tmp_path)

    assert report["secret_leak_count"] >= 1
    assert report["status"] == "failed"


def test_eval_computes_coverage_rates(tmp_path: Path) -> None:
    write_graph(tmp_path, build_graph().model_dump(mode="json"))

    report = eval_lineage_graph.run(tasks_root=tmp_path)

    assert report["field_lineage_coverage"] == 1.0
    assert report["chunk_lineage_coverage"] == 1.0
    assert report["artifact_lineage_coverage"] == 1.0
    assert report["mapping_decision_link_rate"] == 1.0
    assert report["manifest_link_rate"] == 1.0


def test_eval_merges_generated_metrics_with_sources(tmp_path: Path) -> None:
    write_graph(tmp_path / "tasks", build_graph().model_dump(mode="json"))
    metrics = tmp_path / "current_metrics.json"
    metrics.write_text(
        json.dumps(
            {
                "package_verification_rate": 1.0,
                "sources": {
                    "package_verification_rate": "reports/package.json",
                },
            }
        ),
        encoding="utf-8",
    )

    eval_lineage_graph.run(
        tasks_root=tmp_path / "tasks",
        evaluation_metrics_path=metrics,
        out_path=tmp_path / "lineage.json",
    )
    updated = json.loads(metrics.read_text(encoding="utf-8"))

    assert updated["package_verification_rate"] == 1.0
    assert updated["lineage_parse_pass_rate"] == 1.0
    assert updated["lineage_broken_edges"] == 0
    assert updated["lineage_secret_leaks"] == 0
    assert updated["lineage_field_coverage"] == 1.0
    assert updated["sources"]["lineage_field_coverage"].endswith("lineage.json")
