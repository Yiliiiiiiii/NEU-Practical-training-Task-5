"""Evaluate persisted SchemaPack-Lineage graphs without inventing metrics."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.schemas.lineage import LineageGraph  # noqa: E402

SECRET_KEY_PATTERN = re.compile(
    r"(?i)^(?:api[_-]?key|apikey|authorization|bearer|credentials?|password|secret|token)$"
)
SECRET_SUFFIX_PATTERN = re.compile(r"(?i)_(?:api_key|password|secret|token)$")
SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(?:\b(?:authorization|bearer|api[_-]?key|password|secret|token)\b"
    r"|(?:^|[^a-z0-9])sk-[a-z0-9_-]{4,})"
)


def run(
    *,
    tasks_root: str | Path = ROOT / "storage" / "tasks",
    base_url: str | None = None,
    api_key: str | None = None,
    out_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
    evaluation_metrics_path: str | Path | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    inputs = (
        load_api_graphs(base_url, api_key=api_key, timeout=timeout)
        if base_url
        else load_local_graphs(Path(tasks_root))
    )
    report = evaluate(inputs)
    if out_path is not None:
        write_json(Path(out_path), report)
    if markdown_path is not None:
        write_markdown(Path(markdown_path), report)
    if evaluation_metrics_path is not None:
        merge_evaluation_metrics(
            Path(evaluation_metrics_path),
            report,
            source_path=Path(out_path) if out_path is not None else None,
        )
    return report


def load_local_graphs(tasks_root: Path) -> list[tuple[str, Any]]:
    if not tasks_root.exists():
        return []
    inputs: list[tuple[str, Any]] = []
    for path in sorted(tasks_root.rglob("lineage_graph.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            payload = {"_parse_error": str(exc)}
        inputs.append((str(path), payload))
    return inputs


def load_api_graphs(
    base_url: str,
    *,
    api_key: str | None,
    timeout: float,
) -> list[tuple[str, Any]]:
    headers = {"X-API-Key": api_key} if api_key else None
    inputs: list[tuple[str, Any]] = []
    with httpx.Client(
        base_url=base_url.rstrip("/"),
        headers=headers,
        timeout=timeout,
    ) as client:
        page = 1
        while True:
            response = client.get(
                "/api/v1/tasks",
                params={"page": page, "page_size": 100},
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items", []) if isinstance(payload, dict) else []
            if not isinstance(items, list) or not items:
                break
            for item in items:
                task_id = item.get("task_id") if isinstance(item, dict) else None
                if not isinstance(task_id, str):
                    continue
                graph_response = client.get(f"/api/v1/tasks/{task_id}/lineage")
                if graph_response.status_code == 404:
                    continue
                graph_response.raise_for_status()
                inputs.append((f"{base_url}/api/v1/tasks/{task_id}/lineage", graph_response.json()))
            if len(items) < 100:
                break
            page += 1
    return inputs


def evaluate(inputs: list[tuple[str, Any]]) -> dict[str, Any]:
    graphs: list[LineageGraph] = []
    parse_errors: list[dict[str, str]] = []
    secret_leak_count = 0
    for source, payload in inputs:
        secret_leak_count += count_secret_leaks(payload)
        try:
            if isinstance(payload, dict) and "_parse_error" in payload:
                raise ValueError(str(payload["_parse_error"]))
            graphs.append(LineageGraph.model_validate(payload))
        except (ValidationError, ValueError, TypeError) as exc:
            parse_errors.append({"source": source, "error": str(exc)})

    totals = {
        "fields": 0,
        "traced_fields": 0,
        "chunks": 0,
        "traced_chunks": 0,
        "artifacts": 0,
        "traced_artifacts": 0,
        "mappings": 0,
        "linked_mappings": 0,
        "reviews": 0,
        "linked_reviews": 0,
        "knowledge": 0,
        "linked_knowledge": 0,
        "manifest_entries": 0,
        "linked_manifest_entries": 0,
        "orphans": 0,
        "broken_edges": 0,
        "badcase_blocked": 0,
        "llm_auto_accepted": 0,
    }
    for graph in graphs:
        accumulate_graph_metrics(graph, totals)

    graph_count = len(inputs)
    parse_pass_count = len(graphs)
    parse_pass_rate = _rate(parse_pass_count, graph_count, empty=0.0)
    field_coverage = _rate(totals["traced_fields"], totals["fields"])
    chunk_coverage = _rate(totals["traced_chunks"], totals["chunks"])
    artifact_coverage = _rate(totals["traced_artifacts"], totals["artifacts"])
    report = {
        "status": "passed",
        "lineage_graph_count": graph_count,
        "lineage_parse_pass_count": parse_pass_count,
        "lineage_parse_pass_rate": parse_pass_rate,
        "field_lineage_coverage": field_coverage,
        "chunk_lineage_coverage": chunk_coverage,
        "artifact_lineage_coverage": artifact_coverage,
        "mapping_decision_link_rate": _rate(
            totals["linked_mappings"],
            totals["mappings"],
        ),
        "review_link_rate": _rate(totals["linked_reviews"], totals["reviews"]),
        "knowledge_pack_link_rate": _rate(
            totals["linked_knowledge"],
            totals["knowledge"],
        ),
        "badcase_blocked_visible_count": totals["badcase_blocked"],
        "manifest_link_rate": _rate(
            totals["linked_manifest_entries"],
            totals["manifest_entries"],
        ),
        "orphan_node_count": totals["orphans"],
        "broken_edge_count": totals["broken_edges"],
        "secret_leak_count": secret_leak_count,
        "llm_auto_accepted_count": totals["llm_auto_accepted"],
        "parse_errors": parse_errors,
        "thresholds": {
            "lineage_parse_pass_rate": 1.0,
            "field_lineage_coverage": 0.9,
            "chunk_lineage_coverage": 0.9,
            "artifact_lineage_coverage": 0.95,
            "broken_edge_count": 0,
            "secret_leak_count": 0,
            "llm_auto_accepted_count": 0,
        },
    }
    report["status"] = (
        "passed"
        if (
            report["lineage_parse_pass_rate"] == 1.0
            and report["field_lineage_coverage"] >= 0.9
            and report["chunk_lineage_coverage"] >= 0.9
            and report["artifact_lineage_coverage"] >= 0.95
            and report["broken_edge_count"] == 0
            and report["secret_leak_count"] == 0
            and report["llm_auto_accepted_count"] == 0
        )
        else "failed"
    )
    return report


def accumulate_graph_metrics(
    graph: LineageGraph,
    totals: dict[str, int],
) -> None:
    nodes = {node.node_id: node for node in graph.nodes}
    incoming: dict[str, list] = {node_id: [] for node_id in nodes}
    outgoing: dict[str, list] = {node_id: [] for node_id in nodes}
    for edge in graph.edges:
        source_exists = edge.source_node_id in nodes
        target_exists = edge.target_node_id in nodes
        if not source_exists or not target_exists:
            totals["broken_edges"] += 1
            continue
        outgoing[edge.source_node_id].append(edge)
        incoming[edge.target_node_id].append(edge)

    totals["orphans"] += sum(
        not incoming[node_id] and not outgoing[node_id] for node_id in nodes
    )
    schema_nodes = {
        node_id for node_id, node in nodes.items() if node.node_type == "schema_field"
    }
    chunk_nodes = {
        node_id for node_id, node in nodes.items() if node.node_type == "chunk"
    }
    manifest_nodes = {
        node_id
        for node_id, node in nodes.items()
        if node.node_type == "package_manifest_entry"
    }
    mapping_nodes = {
        node_id
        for node_id, node in nodes.items()
        if node.node_type == "mapping_decision"
        and node.metadata.get("decision") != "source_not_present"
    }
    review_nodes = {
        node_id
        for node_id, node in nodes.items()
        if node.node_type == "review_decision"
    }
    knowledge_nodes = {
        node_id
        for node_id, node in nodes.items()
        if node.node_type == "knowledge_pack"
    }

    totals["fields"] += len(schema_nodes)
    totals["traced_fields"] += sum(
        any(
            nodes[edge.source_node_id].node_type
            in {"mapping_decision", "canonical_field", "knowledge_pack"}
            for edge in incoming[node_id]
        )
        for node_id in schema_nodes
    )
    totals["chunks"] += len(chunk_nodes)
    totals["traced_chunks"] += sum(
        any(nodes[edge.source_node_id].node_type == "uir_block" for edge in incoming[node_id])
        for node_id in chunk_nodes
    )
    totals["artifacts"] += len(manifest_nodes)
    totals["traced_artifacts"] += sum(
        any(
            nodes[edge.source_node_id].node_type == "rendered_artifact"
            for edge in incoming[node_id]
        )
        for node_id in manifest_nodes
    )
    totals["manifest_entries"] += len(manifest_nodes)
    totals["linked_manifest_entries"] += sum(bool(incoming[node_id]) for node_id in manifest_nodes)
    totals["mappings"] += len(mapping_nodes)
    totals["linked_mappings"] += sum(
        any(nodes[edge.source_node_id].node_type == "field_candidate" for edge in incoming[node_id])
        and any(nodes[edge.target_node_id].node_type == "schema_field" for edge in outgoing[node_id])
        for node_id in mapping_nodes
    )
    totals["reviews"] += len(review_nodes)
    totals["linked_reviews"] += sum(
        any(nodes[edge.source_node_id].node_type == "mapping_decision" for edge in incoming[node_id])
        for node_id in review_nodes
    )
    totals["knowledge"] += len(knowledge_nodes)
    totals["linked_knowledge"] += sum(
        bool(incoming[node_id] or outgoing[node_id]) for node_id in knowledge_nodes
    )
    totals["badcase_blocked"] += sum(
        nodes[node_id].status == "blocked"
        or "badcase_blocked" in nodes[node_id].risk_flags
        for node_id in mapping_nodes
    )
    totals["llm_auto_accepted"] += sum(
        nodes[node_id].status == "accepted"
        and (
            "llm_suggestion" in nodes[node_id].risk_flags
            or nodes[node_id].metadata.get("strategy") == "llm_fallback"
        )
        for node_id in mapping_nodes
    )


def count_secret_leaks(value: Any) -> int:
    if isinstance(value, dict):
        count = 0
        for key, item in value.items():
            key_text = str(key)
            if SECRET_KEY_PATTERN.fullmatch(key_text) or SECRET_SUFFIX_PATTERN.search(key_text):
                count += 1
            count += count_secret_leaks(item)
        return count
    if isinstance(value, list):
        return sum(count_secret_leaks(item) for item in value)
    if isinstance(value, str):
        return int(bool(SECRET_VALUE_PATTERN.search(value)))
    return 0


def merge_evaluation_metrics(
    path: Path,
    report: dict[str, Any],
    *,
    source_path: Path | None,
) -> None:
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("evaluation metrics must be a JSON object")
    else:
        payload = {}
    source = str(source_path or "scripts/eval_lineage_graph.py").replace("\\", "/")
    updates = {
        "lineage_parse_pass_rate": report["lineage_parse_pass_rate"],
        "lineage_broken_edges": report["broken_edge_count"],
        "lineage_secret_leaks": report["secret_leak_count"],
        "lineage_field_coverage": report["field_lineage_coverage"],
    }
    payload.update(updates)
    sources = payload.get("sources")
    if not isinstance(sources, dict):
        sources = {}
    sources.update({key: source for key in updates})
    payload["sources"] = sources
    write_json(path, payload)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    rows = [
        "# SchemaPack-Lineage Evaluation",
        "",
        f"Status: **{report['status']}**",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in (
        "lineage_graph_count",
        "lineage_parse_pass_count",
        "lineage_parse_pass_rate",
        "field_lineage_coverage",
        "chunk_lineage_coverage",
        "artifact_lineage_coverage",
        "mapping_decision_link_rate",
        "review_link_rate",
        "knowledge_pack_link_rate",
        "manifest_link_rate",
        "badcase_blocked_visible_count",
        "orphan_node_count",
        "broken_edge_count",
        "secret_leak_count",
        "llm_auto_accepted_count",
    ):
        rows.append(f"| `{key}` | {report[key]} |")
    rows.extend(
        [
            "",
            "> Lineage proves traceability and decision history; it does not by itself "
            "prove strict semantic correctness.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows), encoding="utf-8")


def _rate(numerator: int, denominator: int, *, empty: float = 1.0) -> float:
    return round(numerator / denominator, 4) if denominator else empty


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks-root", default=str(ROOT / "storage" / "tasks"))
    parser.add_argument("--base-url")
    parser.add_argument("--api-key")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--out", default=str(ROOT / "reports" / "lineage_eval_report.json"))
    parser.add_argument(
        "--markdown",
        default=str(ROOT / "reports" / "lineage_eval_report.md"),
    )
    parser.add_argument("--evaluation-metrics")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(
        tasks_root=args.tasks_root,
        base_url=args.base_url,
        api_key=args.api_key,
        out_path=args.out,
        markdown_path=args.markdown,
        evaluation_metrics_path=args.evaluation_metrics,
        timeout=args.timeout,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
