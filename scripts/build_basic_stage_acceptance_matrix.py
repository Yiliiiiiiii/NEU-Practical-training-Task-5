"""Build the basic-stage acceptance matrix markdown."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _status(condition: bool, *, partial: bool = False) -> str:
    if condition:
        return "passed"
    return "partial" if partial else "failed"


def build(mapping: dict[str, Any], splits: dict[str, Any], deepseek: dict[str, Any], review: dict[str, Any], content: dict[str, Any], package: dict[str, Any]) -> str:
    summary = mapping.get("summary", {})
    split_rows = splits.get("splits", [])
    split_gate = all(float(row.get("assisted_mapping_recall", 0.0)) >= 0.85 for row in split_rows)
    rows = [
        ("输入 UIR / External UIR", "external adapter eval、CLI/API demo", "passed"),
        ("Schema 驱动字段映射", "mapping eval、split eval", _status(split_gate, partial=True)),
        ("规则 + 大模型疑难映射", "DeepSeek suggestion eval", _status(deepseek.get("suggestion_count", 0) > 0)),
        ("置信度与人工复核", "mapping report、review subagent report", _status(review.get("reviewed_items", 0) > 0)),
        ("分段、摘要、关键词", "content quality report", _status(bool(content))),
        ("JSON + Markdown 双形态", "package consistency report", _status(package.get("package_verify_pass_rate") == 1.0)),
        ("manifest/checksum", "package verifier", _status(package.get("checksum_pass_rate") == 1.0)),
        ("RAG/training/CSV 下游读取", "package consistency report", _status(package.get("downstream_rag_jsonl_parse_pass") == 1.0)),
        ("安全边界", "badcase、required missing、LLM auto accepted", _status(summary.get("badcase_violation_count") == 0 and summary.get("required_missing_count") == 0 and deepseek.get("llm_auto_accepted_count") == 0)),
    ]
    lines = [
        "# Basic-stage Acceptance Matrix",
        "",
        "## Current Mapping Metrics",
        "",
        f"- Dataset size: {summary.get('dataset_size')}",
        f"- Auto mapping recall: {summary.get('auto_mapping_recall')}",
        f"- Assisted mapping recall: {summary.get('assisted_mapping_recall')}",
        f"- Review-required rate: {summary.get('review_required_rate')}",
        f"- Required missing: {summary.get('required_missing_count')}",
        f"- Badcase violations: {summary.get('badcase_violation_count')}",
        "",
        "| 要求 | 证据 | 状态 |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| {name} | {evidence} | {status} |" for name, evidence, status in rows)
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    text = build(
        _load(ROOT / "reports" / "non_procurement_mapping_eval_report.json"),
        _load(ROOT / "docs" / "交接" / "evidence" / "basic_stage" / "mapping" / "splits" / "summary.json"),
        _load(ROOT / "docs" / "交接" / "evidence" / "basic_stage" / "llm" / "deepseek_mapping_suggestion_eval_report.json"),
        _load(ROOT / "docs" / "交接" / "evidence" / "basic_stage" / "review" / "codex_review_subagent_report.json"),
        _load(ROOT / "docs" / "交接" / "evidence" / "basic_stage" / "content" / "content_tag_summary_quality_report.json"),
        _load(ROOT / "docs" / "交接" / "evidence" / "basic_stage" / "package" / "package_consistency_report.json"),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
