"""Build a compact, reproducible demo report from a persisted lineage graph."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.schemas.lineage import LineageGraph  # noqa: E402
from app.services.lineage_query_service import LineageQueryService  # noqa: E402


def run(
    *,
    graph_path: str | Path,
    out_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(graph_path)
    graph = LineageGraph.model_validate(
        json.loads(source.read_text(encoding="utf-8"))
    )
    field_name = _preferred_value(
        graph,
        node_type="schema_field",
        attribute="field_name",
        preferred="title",
    )
    chunk_id = _preferred_value(
        graph,
        node_type="chunk",
        attribute="chunk_id",
    )
    artifact_path = _preferred_value(
        graph,
        node_type="package_manifest_entry",
        attribute="artifact_path",
        preferred="chunks.jsonl",
    )
    query = LineageQueryService()
    showcase: dict[str, Any] = {}
    if field_name:
        showcase["field"] = {
            "root": field_name,
            "query": query.query_field(
                graph,
                field_name,
                direction="upstream",
            ).model_dump(mode="json"),
        }
    if chunk_id:
        showcase["chunk"] = {
            "root": chunk_id,
            "query": query.query_chunk(
                graph,
                chunk_id,
                direction="upstream",
            ).model_dump(mode="json"),
        }
    if artifact_path:
        showcase["artifact"] = {
            "root": artifact_path,
            "query": query.query_artifact(
                graph,
                artifact_path,
                direction="both",
            ).model_dump(mode="json"),
        }
    report = {
        "task_id": graph.task_id,
        "doc_id": graph.doc_id,
        "graph_id": graph.graph_id,
        "lineage_version": graph.lineage_version,
        "summary": graph.summary,
        "showcase": showcase,
        "warning": (
            "Lineage proves traceability and decision history; "
            "it does not prove strict semantic correctness."
        ),
        "source_graph": str(source).replace("\\", "/"),
    }
    if out_path is not None:
        _write_json(Path(out_path), report)
    if markdown_path is not None:
        _write_markdown(Path(markdown_path), report)
    return report


def _preferred_value(
    graph: LineageGraph,
    *,
    node_type: str,
    attribute: str,
    preferred: str | None = None,
) -> str | None:
    values = [
        getattr(node, attribute)
        for node in graph.nodes
        if node.node_type == node_type and isinstance(getattr(node, attribute), str)
    ]
    if preferred in values:
        return preferred
    return sorted(values)[0] if values else None


def _write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    lines = [
        "# SchemaPack-Lineage Demo Report",
        "",
        f"- Task: `{report['task_id']}`",
        f"- Document: `{report['doc_id']}`",
        f"- Graph: `{report['graph_id']}`",
        f"- Nodes / edges: {summary.get('node_count', 0)} / {summary.get('edge_count', 0)}",
        f"- Field coverage: {summary.get('field_lineage_coverage', 0)}",
        f"- Chunk coverage: {summary.get('chunk_lineage_coverage', 0)}",
        f"- Artifact coverage: {summary.get('artifact_lineage_coverage', 0)}",
        "",
        "## Showcase",
        "",
    ]
    for kind, item in report["showcase"].items():
        query_summary = item["query"].get("summary", {})
        lines.append(
            f"- **{kind}** `{item['root']}`: "
            f"{query_summary.get('node_count', 0)} nodes / "
            f"{query_summary.get('edge_count', 0)} edges"
        )
    lines.extend(["", f"> {report['warning']}", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True)
    parser.add_argument(
        "--out",
        default=str(ROOT / "reports" / "lineage_demo_report.json"),
    )
    parser.add_argument(
        "--markdown",
        default=str(ROOT / "reports" / "lineage_demo_report.md"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(
        graph_path=args.graph,
        out_path=args.out,
        markdown_path=args.markdown,
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
