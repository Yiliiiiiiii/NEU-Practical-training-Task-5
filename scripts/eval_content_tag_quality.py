"""Evaluate content/management/quality tag accuracy on real-world chunks."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = (
    ROOT / "examples" / "real_world" / "gold" / "content_organization_gold.jsonl"
)
DEFAULT_UIR_DIR = ROOT / "examples" / "real_world" / "uir"
DEFAULT_JSON = ROOT / "reports" / "content_tag_quality_eval_report.json"
DEFAULT_MD = ROOT / "reports" / "content_tag_quality_eval_report.md"
DEFAULT_STRATEGY = "heading_aware"


def _load_retrieval_module():
    path = ROOT / "scripts" / "eval_chunk_retrieval.py"
    spec = importlib.util.spec_from_file_location("_tag_quality_retrieval", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load retrieval evaluator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RETRIEVAL = _load_retrieval_module()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        rows.append(row)
    return rows


def load_uirs(uir_dir: Path) -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}
    for path in sorted(uir_dir.glob("*/*.json")):
        if path.parent.name == "_rejected":
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        documents[str(document["doc_id"])] = document
    return documents


def _string_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{label} must contain non-empty strings")
    return value


def validate_gold(rows: list[dict[str, Any]], uirs: dict[str, dict[str, Any]]) -> None:
    for index, row in enumerate(rows, start=1):
        doc_id = str(row.get("doc_id", ""))
        label = f"gold row {index} ({doc_id or 'missing doc_id'})"
        if doc_id not in uirs:
            raise ValueError(f"{label}: unknown UIR document")
        block_ids = _string_list(
            row.get("source_block_ids"), label=f"{label}: source_block_ids"
        )
        actual_ids = {
            str(block.get("block_id"))
            for block in uirs[doc_id].get("blocks", [])
            if block.get("block_id")
        }
        unknown = sorted(set(block_ids) - actual_ids)
        if unknown:
            raise ValueError(f"{label}: unknown block reference {unknown[0]}")
        _string_list(
            row.get("expected_content_tags"), label=f"{label}: expected_content_tags"
        )
        _string_list(
            row.get("expected_management_tags"),
            label=f"{label}: expected_management_tags",
        )
        _string_list(
            row.get("expected_quality_tags"), label=f"{label}: expected_quality_tags"
        )
    if len(rows) < 20:
        raise ValueError("content tag quality gold must contain at least 20 samples")


def score_tag_category(
    *,
    expected: set[str],
    actual: set[str],
    known: set[str],
    known_prefixes: tuple[str, ...] = (),
) -> dict[str, Any]:
    true_positive = len(expected & actual)
    precision = _ratio(true_positive, len(actual))
    recall = _ratio(true_positive, len(expected))
    f1 = _ratio(2 * precision * recall, precision + recall)
    unknown_tags = {
        tag
        for tag in actual
        if tag not in known
        and not any(tag.startswith(prefix) for prefix in known_prefixes)
    }
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "unknown_tag_count": len(unknown_tags),
        "missing_tags": sorted(expected - actual),
        "extra_tags": sorted(actual - expected),
        "unknown_tags": sorted(unknown_tags),
    }


def relevant_chunks(
    sample: dict[str, Any], chunks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    wanted = {str(block_id) for block_id in sample.get("source_block_ids", [])}
    return [
        chunk
        for chunk in chunks
        if wanted & {str(block_id) for block_id in chunk.get("source_block_ids", [])}
    ]


def _collect_tags(chunks: list[dict[str, Any]], field: str) -> set[str]:
    return {str(tag) for chunk in chunks for tag in chunk.get(field, []) if tag}


def evaluate_tag_sample(
    sample: dict[str, Any],
    chunks: list[dict[str, Any]],
    known_tags: dict[str, set[str]],
) -> dict[str, Any]:
    categories = {
        "content": (
            set(sample.get("expected_content_tags", [])),
            _collect_tags(chunks, "content_tags"),
        ),
        "management": (
            set(sample.get("expected_management_tags", [])),
            _collect_tags(chunks, "management_tags"),
        ),
        "quality": (
            set(sample.get("expected_quality_tags", [])),
            _collect_tags(chunks, "quality_tags"),
        ),
    }
    scores = {
        category: score_tag_category(
            expected=expected,
            actual=actual,
            known=known_tags[category],
            known_prefixes=KNOWN_TAG_PREFIXES[category],
        )
        for category, (expected, actual) in categories.items()
    }
    expected_total = sum(len(expected) for expected, _ in categories.values())
    covered_total = sum(
        len(expected & actual) for expected, actual in categories.values()
    )
    return {
        "doc_id": sample.get("doc_id"),
        "source_block_ids": sample.get("source_block_ids", []),
        "chunk_ids": [chunk.get("chunk_id") for chunk in chunks],
        "content": scores["content"],
        "management": scores["management"],
        "quality": scores["quality"],
        "tag_coverage": _ratio(covered_total, expected_total),
        "unknown_tag_count": sum(
            int(scores[category]["unknown_tag_count"]) for category in scores
        ),
    }


def _ratio(numerator: int | float, denominator: int | float) -> float:
    return round(float(numerator) / float(denominator), 4) if denominator else 0.0


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _known_tags(gold_rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    known = {
        "content": set(),
        "management": set(),
        "quality": set(),
    }
    for row in gold_rows:
        known["content"].update(
            str(tag) for tag in row.get("expected_content_tags", [])
        )
        known["management"].update(
            str(tag) for tag in row.get("expected_management_tags", [])
        )
        known["quality"].update(
            str(tag) for tag in row.get("expected_quality_tags", [])
        )
    for schema_id in RETRIEVAL.CATALOG:
        config = RETRIEVAL.default_options(DEFAULT_STRATEGY, schema_id)
        tag_rules = config.get("tag_rules", {})
        content = tag_rules.get("content", {})
        known["content"].update(str(tag) for tag in content.get("base_tags", []))
        known["content"].update(
            str(rule["tag"])
            for rule in content.get("rules", [])
            if isinstance(rule, dict) and rule.get("tag")
        )
        management = tag_rules.get("management", {})
        known["management"].update(
            str(tag) for tag in management.get("static_tags", [])
        )
        quality = tag_rules.get("quality", {})
        known["quality"].update(
            str(tag) for tag in quality.get("enabled_builtin_rules", [])
        )
    return known


KNOWN_TAG_PREFIXES = {
    "content": (),
    "management": (
        "schema:",
        "template_version:",
    ),
    "quality": (),
}


def build_report(
    *,
    gold_rows: list[dict[str, Any]],
    chunks_by_doc: dict[str, list[dict[str, Any]]],
    strategy: str,
) -> dict[str, Any]:
    known_tags = _known_tags(gold_rows)
    samples = [
        evaluate_tag_sample(
            sample,
            relevant_chunks(sample, chunks_by_doc.get(str(sample["doc_id"]), [])),
            known_tags,
        )
        for sample in gold_rows
    ]
    metrics = {
        "content_tag_precision": _mean(
            [float(item["content"]["precision"]) for item in samples]
        ),
        "content_tag_recall": _mean(
            [float(item["content"]["recall"]) for item in samples]
        ),
        "content_tag_f1": _mean([float(item["content"]["f1"]) for item in samples]),
        "management_tag_precision": _mean(
            [float(item["management"]["precision"]) for item in samples]
        ),
        "management_tag_recall": _mean(
            [float(item["management"]["recall"]) for item in samples]
        ),
        "management_tag_f1": _mean(
            [float(item["management"]["f1"]) for item in samples]
        ),
        "quality_tag_precision": _mean(
            [float(item["quality"]["precision"]) for item in samples]
        ),
        "quality_tag_recall": _mean(
            [float(item["quality"]["recall"]) for item in samples]
        ),
        "quality_tag_f1": _mean([float(item["quality"]["f1"]) for item in samples]),
        "tag_coverage": _mean([float(item["tag_coverage"]) for item in samples]),
        "unknown_tag_count": sum(int(item["unknown_tag_count"]) for item in samples),
    }
    failures = [
        item
        for item in samples
        if item["tag_coverage"] < 1.0 or item["unknown_tag_count"] > 0
    ]
    return {
        "status": "completed",
        "strategy": strategy,
        "sample_count": len(samples),
        "metrics": metrics,
        "samples": samples,
        "failures": failures,
    }


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Content Tag Quality Eval Report",
        "",
        f"- Status: {report['status']}",
        f"- Strategy: {report['strategy']}",
        f"- Samples: {report['sample_count']}",
        "",
        "| Category | Precision | Recall | F1 |",
        "| --- | ---: | ---: | ---: |",
        f"| content | {metrics['content_tag_precision']:.4f} | {metrics['content_tag_recall']:.4f} | {metrics['content_tag_f1']:.4f} |",
        f"| management | {metrics['management_tag_precision']:.4f} | {metrics['management_tag_recall']:.4f} | {metrics['management_tag_f1']:.4f} |",
        f"| quality | {metrics['quality_tag_precision']:.4f} | {metrics['quality_tag_recall']:.4f} | {metrics['quality_tag_f1']:.4f} |",
        "",
        f"- Tag coverage: {metrics['tag_coverage']:.4f}",
        f"- Unknown tag count: {metrics['unknown_tag_count']}",
        "",
        "## Failure samples",
        "",
    ]
    if report["failures"]:
        for item in report["failures"][:50]:
            lines.append(
                f"- {item['doc_id']} blocks={item['source_block_ids']} "
                f"coverage={item['tag_coverage']:.4f} unknown={item['unknown_tag_count']}"
            )
    else:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def write_reports(
    report: dict[str, Any], *, output_json: Path, output_md: Path
) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output_md.write_text(render_markdown(report), encoding="utf-8")


def run_evaluation(
    *,
    gold_path: Path = DEFAULT_GOLD,
    uir_dir: Path = DEFAULT_UIR_DIR,
    output_json: Path = DEFAULT_JSON,
    output_md: Path = DEFAULT_MD,
    strategy: str = DEFAULT_STRATEGY,
) -> dict[str, Any]:
    gold_rows = load_jsonl(gold_path)
    uirs = load_uirs(uir_dir)
    validate_gold(gold_rows, uirs)
    selected_docs = {str(row["doc_id"]): uirs[str(row["doc_id"])] for row in gold_rows}
    chunks_by_doc = RETRIEVAL.generate_chunks_for_strategy(
        selected_docs, strategy=strategy
    )
    report = build_report(
        gold_rows=gold_rows, chunks_by_doc=chunks_by_doc, strategy=strategy
    )
    write_reports(report, output_json=output_json, output_md=output_md)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-path", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--uir-dir", type=Path, default=DEFAULT_UIR_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--strategy", default=DEFAULT_STRATEGY)
    args = parser.parse_args()
    try:
        report = run_evaluation(
            gold_path=args.gold_path,
            uir_dir=args.uir_dir,
            output_json=args.output_json,
            output_md=args.output_md,
            strategy=args.strategy,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    print(
        json.dumps(
            {
                "status": report["status"],
                "sample_count": report["sample_count"],
                "tag_coverage": report["metrics"]["tag_coverage"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
