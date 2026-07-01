"""Evaluate lightweight summary faithfulness rules on real-world chunks."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "examples" / "real_world" / "gold" / "content_organization_gold.jsonl"
DEFAULT_UIR_DIR = ROOT / "examples" / "real_world" / "uir"
DEFAULT_JSON = ROOT / "reports" / "summary_faithfulness_eval_report.json"
DEFAULT_MD = ROOT / "reports" / "summary_faithfulness_eval_report.md"
DEFAULT_STRATEGY = "heading_aware"
MAX_SUMMARY_SOURCE_RATIO = 0.7


def _load_retrieval_module():
    path = ROOT / "scripts" / "eval_chunk_retrieval.py"
    spec = importlib.util.spec_from_file_location("_summary_retrieval", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load retrieval evaluator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RETRIEVAL = _load_retrieval_module()


DATE_RE = re.compile(r"\d{4}[-年]\d{1,2}(?:[-月]\d{1,2}[日]?)?|\d{4}年")
AMOUNT_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:万?元|亿元|%|万元)")
ORG_RE = re.compile(
    r"[\u4e00-\u9fff]{2,24}(?:政府|委员会|办公室|管理局|财政局|公司|中心|学校|学院|医院|机构)"
)
TABLE_NUMBER_RE = re.compile(
    r"(?P<number>\d+(?:\.\d+)?)\s*(?P<unit>亿元|万元|元|%|年|月|日|个|项|家|人|次|套|台)?"
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
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


def _string_list(value: Any, *, label: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"{label} must be a {'possibly empty ' if allow_empty else ''}list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{label} must contain non-empty strings")
    return value


def validate_gold(rows: list[dict[str, Any]], uirs: dict[str, dict[str, Any]]) -> None:
    for index, row in enumerate(rows, start=1):
        doc_id = str(row.get("doc_id", ""))
        label = f"gold row {index} ({doc_id or 'missing doc_id'})"
        if doc_id not in uirs:
            raise ValueError(f"{label}: unknown UIR document")
        block_ids = _string_list(row.get("source_block_ids"), label=f"{label}: source_block_ids")
        actual_ids = {
            str(block.get("block_id"))
            for block in uirs[doc_id].get("blocks", [])
            if block.get("block_id")
        }
        unknown = sorted(set(block_ids) - actual_ids)
        if unknown:
            raise ValueError(f"{label}: unknown block reference {unknown[0]}")
        _string_list(row.get("summary_must_include"), label=f"{label}: summary_must_include")
        _string_list(
            row.get("summary_must_not_include"),
            label=f"{label}: summary_must_not_include",
            allow_empty=True,
        )
    if len(rows) < 20:
        raise ValueError("summary faithfulness gold must contain at least 20 samples")


def _block_text(block: dict[str, Any]) -> str:
    text = str(block.get("text") or "")
    if text:
        return text
    rows = block.get("attributes", {}).get("rows", [])
    if not isinstance(rows, list):
        return text
    values = []
    for row in rows:
        if isinstance(row, dict):
            values.extend(str(value) for value in row.values() if value)
    return " ".join(values)


def source_text_for_block_ids(block_ids: set[str], uir: dict[str, Any]) -> str:
    return "\n".join(
        _block_text(block)
        for block in uir.get("blocks", [])
        if str(block.get("block_id")) in block_ids
    )


def relevant_chunks(sample: dict[str, Any], chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = {str(block_id) for block_id in sample.get("source_block_ids", [])}
    return [
        chunk
        for chunk in chunks
        if wanted & {str(block_id) for block_id in chunk.get("source_block_ids", [])}
    ]


def _missing_tokens(tokens: list[str], text: str) -> list[str]:
    return sorted({token for token in tokens if token and token not in text})


def _new_pattern_values(pattern: re.Pattern[str], summary: str, source_text: str) -> list[str]:
    return sorted({match.group(0).strip() for match in pattern.finditer(summary) if match.group(0).strip() not in source_text})


def _summary_text(chunks: list[dict[str, Any]]) -> str:
    return "\n".join(str(chunk.get("summary", "")).strip() for chunk in chunks if chunk.get("summary")).strip()


def table_rows_for_block_ids(block_ids: set[str], uir: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for block in uir.get("blocks", []):
        if str(block.get("block_id")) not in block_ids:
            continue
        block_rows = block.get("attributes", {}).get("rows", [])
        if not isinstance(block_rows, list):
            continue
        for row in block_rows:
            if isinstance(row, dict):
                rows.append([str(value) for value in row.values() if value is not None])
            elif isinstance(row, list):
                rows.append([str(value) for value in row if value is not None])
    return rows


def _normalized_table_number(match: re.Match[str]) -> tuple[str, str]:
    try:
        number = Decimal(match.group("number")).normalize()
    except InvalidOperation:
        number = Decimal(0)
    return (format(number, "f"), match.group("unit") or "")


def _table_row_label(cells: list[str]) -> str | None:
    for cell in cells:
        if TABLE_NUMBER_RE.search(cell):
            continue
        label = TABLE_NUMBER_RE.sub("", cell)
        label = re.sub(r"[\s:：,，。;；()（）]+", "", label)
        if len(label) >= 2:
            return label
    return None


def _table_contexts(
    table_rows: list[list[str]],
) -> list[tuple[str, str | None, set[tuple[str, str]]]]:
    header: list[str] | None = None
    data_rows = table_rows
    if table_rows and len(table_rows[0]) > 1:
        first_row = table_rows[0]
        same_width = all(len(row) == len(first_row) for row in table_rows[1:])
        has_numeric_data = any(
            TABLE_NUMBER_RE.search(cell)
            for row in table_rows[1:]
            for cell in row[1:]
        )
        if same_width and has_numeric_data and _table_row_label(first_row):
            header = first_row
            data_rows = table_rows[1:]
    contexts: list[tuple[str, str | None, set[tuple[str, str]]]] = []
    for cells in data_rows:
        label = _table_row_label(cells)
        if not label:
            continue
        if header and len(header) == len(cells):
            row_allowed: set[tuple[str, str]] = set()
            for index, cell in enumerate(cells[1:], start=1):
                allowed = {
                    _normalized_table_number(match)
                    for match in TABLE_NUMBER_RE.finditer(cell)
                }
                row_allowed.update(allowed)
                column = re.sub(r"\s+", "", header[index])
                if allowed and column:
                    contexts.append((label, column, allowed))
            if row_allowed:
                contexts.append((label, None, row_allowed))
            continue
        allowed = {
            _normalized_table_number(match)
            for cell in cells[1:]
            for match in TABLE_NUMBER_RE.finditer(cell)
        }
        if allowed:
            contexts.append((label, None, allowed))
    return contexts


def _is_numeric_column_anchor(
    table_summary: str,
    match: re.Match[str],
    contexts: list[tuple[str, str | None, set[tuple[str, str]]]],
) -> bool:
    matched_text = re.sub(r"\s+", "", match.group(0))
    for label, column, _allowed in contexts:
        if column != matched_text:
            continue
        row_position = table_summary.rfind(label, 0, match.start())
        if row_position < 0:
            continue
        boundary = row_position + len(label)
        for separator in (";", "；", ",", "，", "|", "\n"):
            separator_position = table_summary.rfind(separator, boundary, match.start())
            if separator_position >= 0:
                boundary = max(boundary, separator_position + len(separator))
        if re.fullmatch(r"[\s:：=\-]*", table_summary[boundary : match.start()]):
            return True
    return False


def _table_number_violations(
    sample: dict[str, Any],
    chunks: list[dict[str, Any]],
    table_rows: list[list[str]],
) -> list[str]:
    table_block_ids = {str(value) for value in sample.get("table_block_ids", [])}
    if not table_block_ids or not table_rows:
        return []
    table_summary = _summary_text(
        [
            chunk
            for chunk in chunks
            if table_block_ids
            & {str(block_id) for block_id in chunk.get("source_block_ids", [])}
        ]
    )
    contexts = _table_contexts(table_rows)
    violations: set[str] = set()
    for match in TABLE_NUMBER_RE.finditer(table_summary):
        if _is_numeric_column_anchor(table_summary, match, contexts):
            continue
        column_matches: list[
            tuple[int, int, str, str | None, set[tuple[str, str]]]
        ] = []
        row_matches: list[tuple[int, int, str, str | None, set[tuple[str, str]]]] = []
        for label, column, allowed in contexts:
            row_position = table_summary.rfind(label, 0, match.start())
            if row_position < 0:
                continue
            position = row_position
            anchor_length = len(label)
            if column:
                column_position = table_summary.rfind(column, row_position, match.start())
                if column_position < 0:
                    continue
                position = max(position, column_position)
                anchor_length = len(column)
            context_match = (position, anchor_length, label, column, allowed)
            if column:
                column_matches.append(context_match)
            else:
                row_matches.append(context_match)
        preceding = column_matches or row_matches
        if not preceding:
            continue
        position, anchor_length, label, column, allowed = max(
            preceding, key=lambda item: item[0]
        )
        if match.start() - (position + anchor_length) > 80:
            continue
        normalized = _normalized_table_number(match)
        if normalized not in allowed:
            context = f"{label}/{column}" if column else label
            violations.add(f"{context}:{match.group(0).strip()}")
    return sorted(violations)


def evaluate_summary_sample(
    sample: dict[str, Any],
    chunks: list[dict[str, Any]],
    source_text: str,
    *,
    table_rows: list[list[str]] | None = None,
) -> dict[str, Any]:
    summary = _summary_text(chunks)
    must_include = [str(item) for item in sample.get("summary_must_include", [])]
    must_not_include = [str(item) for item in sample.get("summary_must_not_include", [])]
    missing_include = _missing_tokens(must_include, summary)
    must_not_violations = sorted({item for item in must_not_include if item in summary})
    new_dates = _new_pattern_values(DATE_RE, summary, source_text)
    new_amounts = _new_pattern_values(AMOUNT_RE, summary, source_text)
    new_orgs = _new_pattern_values(ORG_RE, summary, source_text)
    table_number_violations = _table_number_violations(sample, chunks, table_rows or [])
    max_length = max(1, int(len(source_text) * MAX_SUMMARY_SOURCE_RATIO))
    overlong = len(summary) > max_length
    passed = not any(
        [
            not summary,
            missing_include,
            must_not_violations,
            new_dates,
            new_amounts,
            new_orgs,
            table_number_violations,
            overlong,
        ]
    )
    return {
        "doc_id": sample.get("doc_id"),
        "source_block_ids": sample.get("source_block_ids", []),
        "chunk_ids": [chunk.get("chunk_id") for chunk in chunks],
        "passed": passed,
        "summary": summary,
        "missing_must_include": missing_include,
        "must_include_hit_rate": _ratio(len(must_include) - len(missing_include), len(must_include)),
        "must_not_include_violations": must_not_violations,
        "new_date_violations": new_dates,
        "new_amount_violations": new_amounts,
        "new_org_violations": new_orgs,
        "table_number_violations": table_number_violations,
        "overlong_summary": overlong,
        "empty_summary": not bool(summary),
    }


def _ratio(numerator: int | float, denominator: int | float) -> float:
    return round(float(numerator) / float(denominator), 4) if denominator else 0.0


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def build_report(
    *,
    gold_rows: list[dict[str, Any]],
    uirs: dict[str, dict[str, Any]],
    chunks_by_doc: dict[str, list[dict[str, Any]]],
    strategy: str,
) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    for sample in gold_rows:
        doc_id = str(sample["doc_id"])
        chunks = relevant_chunks(sample, chunks_by_doc.get(doc_id, []))
        source_block_ids = {
            str(block_id)
            for chunk in chunks
            for block_id in chunk.get("source_block_ids", [])
            if block_id
        } | {str(block_id) for block_id in sample.get("source_block_ids", [])}
        samples.append(
            evaluate_summary_sample(
                sample,
                chunks,
                source_text_for_block_ids(source_block_ids, uirs[doc_id]),
                table_rows=table_rows_for_block_ids(
                    {str(block_id) for block_id in sample.get("table_block_ids", [])},
                    uirs[doc_id],
                ),
            )
        )
    failures = [sample for sample in samples if not sample["passed"]]
    metrics = {
        "passed": len(samples) - len(failures),
        "failed": len(failures),
        "pass_rate": _ratio(len(samples) - len(failures), len(samples)),
        "passed_count": len(samples) - len(failures),
        "failed_count": len(failures),
        "faithfulness_pass_rate": _ratio(len(samples) - len(failures), len(samples)),
        "new_date_violation": sum(bool(item["new_date_violations"]) for item in samples),
        "new_amount_violation": sum(bool(item["new_amount_violations"]) for item in samples),
        "new_org_violation": sum(bool(item["new_org_violations"]) for item in samples),
        "new_date_violation_count": sum(bool(item["new_date_violations"]) for item in samples),
        "new_amount_violation_count": sum(bool(item["new_amount_violations"]) for item in samples),
        "new_org_violation_count": sum(bool(item["new_org_violations"]) for item in samples),
        "must_include_hit_rate": _mean([float(item["must_include_hit_rate"]) for item in samples]),
        "must_not_include_violation_count": sum(bool(item["must_not_include_violations"]) for item in samples),
        "overlong_summary_count": sum(bool(item["overlong_summary"]) for item in samples),
        "empty_summary_count": sum(bool(item["empty_summary"]) for item in samples),
        "changed_table_number_count": sum(bool(item["table_number_violations"]) for item in samples),
    }
    return {
        "status": "completed",
        "strategy": strategy,
        "sample_count": len(samples),
        "passed": metrics["passed"],
        "failed": metrics["failed"],
        "pass_rate": metrics["pass_rate"],
        "metrics": metrics,
        "samples": samples,
        "failures": failures,
    }


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Summary Faithfulness Eval Report",
        "",
        f"- Status: {report['status']}",
        f"- Strategy: {report['strategy']}",
        f"- Samples: {report['sample_count']}",
        f"- Pass rate: {metrics['faithfulness_pass_rate']:.4f}",
        f"- Must-include hit rate: {metrics['must_include_hit_rate']:.4f}",
        f"- New date violations: {metrics['new_date_violation_count']}",
        f"- New amount violations: {metrics['new_amount_violation_count']}",
        f"- New organization violations: {metrics['new_org_violation_count']}",
        "",
        "## Failures",
        "",
    ]
    if report["failures"]:
        for item in report["failures"][:50]:
            lines.append(
                f"- {item['doc_id']} blocks={item['source_block_ids']} chunks={item['chunk_ids']} "
                f"missing={item['missing_must_include']} forbidden={item['must_not_include_violations']}"
            )
    else:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def write_reports(report: dict[str, Any], *, output_json: Path, output_md: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
    chunks_by_doc = RETRIEVAL.generate_chunks_for_strategy(selected_docs, strategy=strategy)
    report = build_report(gold_rows=gold_rows, uirs=uirs, chunks_by_doc=chunks_by_doc, strategy=strategy)
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
                "faithfulness_pass_rate": report["metrics"]["faithfulness_pass_rate"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
