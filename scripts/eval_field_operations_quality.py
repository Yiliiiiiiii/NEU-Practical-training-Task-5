"""Evaluate deterministic field rename, merge, split, and validate operations."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _normalize_name(value: str) -> str:
    return re.sub(r"[\s_\-]+", "", value.strip().lower())


ALIASES = {
    "title": {"title", "标题", "政策标题", "会议名称", "事项名称"},
    "issuer": {"issuer", "发文机关", "发布单位", "制定机关"},
    "publish_date": {"publish_date", "发布日期", "发布时间", "公布日期"},
    "service_object": {"服务对象", "适用对象", "申报主体", "各有关单位"},
    "contact": {"联系电话", "咨询电话", "联系方式"},
}


def rename_field(source_name: str) -> str | None:
    normalized = _normalize_name(source_name)
    for target, aliases in ALIASES.items():
        if normalized in {_normalize_name(alias) for alias in aliases}:
            return target
    return None


def merge_fields(values: list[str]) -> str:
    return "\n".join(value.strip() for value in values if value.strip())


def split_field(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[；;\n]+", value) if item.strip()]


def validate_field(field: str, value: Any) -> tuple[bool, str | None]:
    if field in {"title", "issuer", "service_object"}:
        return (isinstance(value, str) and bool(value.strip()), field)
    if field == "publish_date":
        return (
            isinstance(value, str)
            and bool(re.fullmatch(r"20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}日?", value)),
            field,
        )
    if field == "contact":
        return (
            isinstance(value, str)
            and bool(re.search(r"(?:1[3-9]\d{9}|0\d{2,3}[-\s]?\d{7,8})", value)),
            field,
        )
    return (False, field)


def _cases() -> list[dict[str, Any]]:
    return [
        {"op": "rename", "input": "标题", "expected": "title"},
        {"op": "rename", "input": "发布单位", "expected": "issuer"},
        {"op": "rename", "input": "各有关单位", "expected": "service_object"},
        {"op": "merge", "input": ["财政部 教育部", "中国人民银行 金融监管总局"], "expected": "财政部 教育部\n中国人民银行 金融监管总局"},
        {"op": "split", "input": "提交申请；部门审核；办结", "expected": ["提交申请", "部门审核", "办结"]},
        {"op": "validate", "field": "publish_date", "input": "2025-01-16", "expected": True},
        {"op": "validate", "field": "contact", "input": "010-12345678", "expected": True},
        {"op": "validate", "field": "publish_date", "input": "网页抓取时间", "expected": False},
    ]


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    op = case["op"]
    if op == "rename":
        actual = rename_field(str(case["input"]))
    elif op == "merge":
        actual = merge_fields([str(item) for item in case["input"]])
    elif op == "split":
        actual = split_field(str(case["input"]))
    elif op == "validate":
        actual, _path = validate_field(str(case["field"]), case["input"])
    else:
        raise ValueError(f"unsupported op: {op}")
    passed = actual == case["expected"]
    return {**case, "actual": actual, "passed": passed}


def build_report() -> dict[str, Any]:
    results = [evaluate_case(case) for case in _cases()]
    total = len(results)
    passed = sum(1 for item in results if item["passed"])
    unsafe = sum(
        1
        for item in results
        if item["op"] == "validate" and item["expected"] is False and item["actual"] is True
    )
    by_op: dict[str, dict[str, int]] = {}
    for item in results:
        row = by_op.setdefault(item["op"], {"passed": 0, "total": 0})
        row["total"] += 1
        row["passed"] += int(bool(item["passed"]))
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "case_count": total,
        "passed_count": passed,
        "field_operation_accuracy": passed / total if total else 0.0,
        "unsafe_operation_count": unsafe,
        "by_operation": {
            op: {**row, "accuracy": row["passed"] / row["total"] if row["total"] else 0.0}
            for op, row in sorted(by_op.items())
        },
        "cases": results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Field Operation Quality",
        "",
        f"- Case count: {report['case_count']}",
        f"- Accuracy: {report['field_operation_accuracy']:.3f}",
        f"- Unsafe operation count: {report['unsafe_operation_count']}",
        "",
        "| Operation | Passed | Total | Accuracy |",
        "| --- | ---: | ---: | ---: |",
    ]
    for op, row in report["by_operation"].items():
        lines.append(f"| {op} | {row['passed']} | {row['total']} | {row['accuracy']:.3f} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.out_md.write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
