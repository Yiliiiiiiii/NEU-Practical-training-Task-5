"""Evaluate Topic 5 standard UIR mapping quality."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.mapping_template import MappingTemplate  # noqa: E402
from app.schemas.target_schema import TargetSchema  # noqa: E402
from app.schemas.topic5_convert import Topic5ConvertRequest  # noqa: E402
from app.services.topic5_conversion_service import Topic5ConversionService  # noqa: E402


DEFAULT_DATASET = ROOT / "eval" / "topic5_standard_uir"
DEFAULT_OUT = ROOT / "reports" / "topic5_standard_uir_mapping.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "topic5_standard_uir_mapping.md"


@dataclass(frozen=True)
class Topic5EvalDataset:
    root: Path
    split: str
    manifest_rows: list[dict[str, Any]]
    items: list[dict[str, Any]]
    gold_by_doc: dict[str, list[dict[str, Any]]]
    negative_pairs: list[dict[str, Any]]
    required_fields: dict[str, list[str]]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            rows.append(value)
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def load_dataset(dataset_root: Path, split: str) -> Topic5EvalDataset:
    dataset_root = dataset_root.resolve()
    manifest_rows = load_jsonl(dataset_root / "manifest.jsonl")
    manifest_by_item = {
        str(row["uir_path"]).removeprefix("uir/"): row for row in manifest_rows
    }
    if split == "all":
        item_keys = sorted(manifest_by_item)
    else:
        split_payload = load_json(dataset_root / "splits" / f"{split}.json")
        item_keys = [str(item) for item in split_payload.get("items", [])]

    items: list[dict[str, Any]] = []
    for item_key in item_keys:
        row = dict(manifest_by_item[item_key])
        row["uir"] = load_json(dataset_root / str(row["uir_path"]))
        items.append(row)

    gold_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in load_jsonl(dataset_root / "gold" / "mapping_gold.jsonl"):
        gold_by_doc[str(row["doc_id"])].append(row)

    return Topic5EvalDataset(
        root=dataset_root,
        split=split,
        manifest_rows=manifest_rows,
        items=items,
        gold_by_doc=dict(gold_by_doc),
        negative_pairs=load_jsonl(dataset_root / "gold" / "negative_pairs.jsonl"),
        required_fields=load_json(dataset_root / "gold" / "required_fields.json"),
    )


def _schema_path(schema_id: str) -> Path:
    schema_pack_path = ROOT / "schema_packs" / "examples" / schema_id / "target_schema.json"
    if schema_pack_path.is_file():
        return schema_pack_path
    production_like = ROOT / "examples" / "production_like" / "schemas" / f"{schema_id}_v1.json"
    if production_like.is_file():
        return production_like
    raise FileNotFoundError(f"target schema not found for {schema_id}")


def _template_path(schema_id: str) -> Path | None:
    path = ROOT / "examples" / "production_like" / "mapping_templates" / f"{schema_id}_base_v1.json"
    return path if path.is_file() else None


def load_schema_and_template(schema_id: str) -> tuple[TargetSchema, MappingTemplate]:
    schema_payload = load_json(_schema_path(schema_id))
    schema = TargetSchema.model_validate(schema_payload)
    template_path = _template_path(schema_id)
    if template_path is not None:
        return schema, MappingTemplate.model_validate(load_json(template_path))
    aliases = {
        field.field_id: [field.field_id, field.name, field.display_name, *field.aliases]
        for field in schema.fields
    }
    return schema, MappingTemplate(
        template_id=f"{schema_id}_base_v1",
        schema_id=schema_id,
        name=f"{schema_id} benchmark rules",
        version=schema.version,
        aliases=aliases,
    )


def source_name(mapping: dict[str, Any]) -> str | None:
    source = mapping.get("source_field")
    if isinstance(source, dict) and isinstance(source.get("source_name"), str):
        return source["source_name"]
    value = mapping.get("source_name") or mapping.get("source_field_name")
    return value if isinstance(value, str) else None


def source_path(mapping: dict[str, Any]) -> str | None:
    source = mapping.get("source_field")
    if isinstance(source, dict) and isinstance(source.get("source_path"), str):
        return source["source_path"]
    value = mapping.get("source_path")
    return value if isinstance(value, str) else None


def target_field(mapping: dict[str, Any]) -> str | None:
    value = mapping.get("target_field_id") or mapping.get("field_id")
    return value if isinstance(value, str) else None


def accepted_mappings(mapping_report: dict[str, Any]) -> list[dict[str, Any]]:
    mappings = mapping_report.get("mappings", [])
    if not isinstance(mappings, list):
        return []
    return [
        item
        for item in mappings
        if isinstance(item, dict) and item.get("status", "accepted") == "accepted"
    ]


def review_required_items(mapping_report: dict[str, Any]) -> list[dict[str, Any]]:
    items = mapping_report.get("review_required_items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def gold_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["target_field_id"]), str(row["source_path"])


def mapping_key(row: dict[str, Any]) -> tuple[str, str | None]:
    return str(target_field(row)), source_path(row)


def supports_gold(row: dict[str, Any], gold: dict[str, Any]) -> bool:
    return target_field(row) == gold.get("target_field_id") and (
        source_path(row) == gold.get("source_path")
        or source_name(row) == gold.get("source_name")
    )


def detect_badcase_violations(
    mapping_report: dict[str, Any],
    negative_pairs: list[dict[str, Any]],
    *,
    schema_id: str,
    doc_id: str,
) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for mapping in accepted_mappings(mapping_report):
        target = target_field(mapping)
        name = source_name(mapping)
        path = source_path(mapping)
        for negative in negative_pairs:
            if negative.get("schema_id") != schema_id:
                continue
            if negative.get("target_field_id") != target:
                continue
            pattern = negative.get("source_pattern")
            if not isinstance(pattern, str):
                continue
            haystacks = [value for value in (name, path) if isinstance(value, str)]
            if any(re.search(pattern, value, flags=re.IGNORECASE) for value in haystacks):
                violations.append(
                    {
                        "doc_id": doc_id,
                        "schema_id": schema_id,
                        "target_field_id": target,
                        "source_name": name,
                        "source_path": path,
                        "reason": str(negative.get("reason") or "negative_pair"),
                        "severity": str(negative.get("severity") or "block"),
                    }
                )
    return violations


def detect_required_missing(
    mapping_report: dict[str, Any],
    *,
    schema_id: str,
    required_fields: dict[str, list[str]],
) -> list[str]:
    accepted_targets = {target_field(item) for item in accepted_mappings(mapping_report)}
    review_targets = {target_field(item) for item in review_required_items(mapping_report)}
    resolved = {item for item in accepted_targets | review_targets if item}
    return sorted(set(required_fields.get(schema_id, [])) - resolved)


def evaluate_mapping_rows(
    rows: list[dict[str, Any]],
    *,
    gold_by_doc: dict[str, list[dict[str, Any]]],
    negative_pairs: list[dict[str, Any]],
    required_fields: dict[str, list[str]],
) -> list[dict[str, Any]]:
    evaluated: list[dict[str, Any]] = []
    for row in rows:
        doc_id = str(row["doc_id"])
        schema_id = str(row["schema_id"])
        mapping_report = row.get("mapping_report", {})
        mapping_report = mapping_report if isinstance(mapping_report, dict) else {}
        accepted = accepted_mappings(mapping_report)
        review_items = review_required_items(mapping_report)
        gold_rows = gold_by_doc.get(doc_id, [])
        gold_keys = {gold_key(gold) for gold in gold_rows}

        auto_tp = 0
        for mapping in accepted:
            key = mapping_key(mapping)
            if key in gold_keys:
                auto_tp += 1
        auto_fp = len(accepted) - auto_tp
        auto_fn = len(gold_rows) - auto_tp
        assisted_tp = sum(
            1
            for gold in gold_rows
            if any(supports_gold(mapping, gold) for mapping in accepted)
            or any(supports_gold(item, gold) for item in review_items)
        )
        total_target_fields = mapping_report.get("summary", {}).get("total_target_fields")
        if not isinstance(total_target_fields, int | float) or total_target_fields <= 0:
            total_target_fields = len(required_fields.get(schema_id, [])) or len(gold_rows)
        badcases = detect_badcase_violations(
            mapping_report,
            negative_pairs,
            schema_id=schema_id,
            doc_id=doc_id,
        )
        required_missing = detect_required_missing(
            mapping_report,
            schema_id=schema_id,
            required_fields=required_fields,
        )
        evaluated.append(
            {
                **row,
                "gold_count": len(gold_rows),
                "auto_tp": auto_tp,
                "auto_fp": auto_fp,
                "auto_fn": auto_fn,
                "assisted_tp": assisted_tp,
                "review_required_count": len(review_items),
                "total_target_fields": int(total_target_fields),
                "required_missing": required_missing,
                "badcase_violations": badcases,
            }
        )
    return evaluated


def ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def rounded(value: float) -> float:
    return round(value, 4)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    auto_tp = sum(int(row.get("auto_tp", 0)) for row in rows)
    auto_fp = sum(int(row.get("auto_fp", 0)) for row in rows)
    auto_fn = sum(int(row.get("auto_fn", 0)) for row in rows)
    assisted_tp = sum(int(row.get("assisted_tp", 0)) for row in rows)
    total_gold = sum(int(row.get("gold_count", 0)) for row in rows)
    review_required_count = sum(int(row.get("review_required_count", 0)) for row in rows)
    total_target_fields = sum(int(row.get("total_target_fields", 0)) for row in rows)
    required_missing = sum(len(row.get("required_missing", [])) for row in rows)
    badcase_violations = sum(len(row.get("badcase_violations", [])) for row in rows)
    conversion_passed = sum(1 for row in rows if row.get("conversion_passed"))
    verified_rows = [
        row for row in rows if row.get("package_verifier_passed") is not None
    ]
    package_verifier_passed = sum(
        1 for row in verified_rows if row.get("package_verifier_passed") is True
    )
    precision = ratio(auto_tp, auto_tp + auto_fp)
    recall = ratio(auto_tp, auto_tp + auto_fn)
    return {
        "dataset_size": len(rows),
        "sample_count": len(rows),
        "auto_precision": rounded(precision),
        "auto_recall": rounded(recall),
        "auto_f1": rounded(ratio(2 * precision * recall, precision + recall)),
        "assisted_recall": rounded(ratio(assisted_tp, total_gold)),
        "review_required_rate": rounded(ratio(review_required_count, total_target_fields)),
        "required_missing": required_missing,
        "badcase_violations": badcase_violations,
        "conversion_success_rate": rounded(ratio(conversion_passed, len(rows))),
        "package_verifier_pass_rate": (
            rounded(ratio(package_verifier_passed, len(verified_rows)))
            if verified_rows
            else None
        ),
        "package_verified_count": len(verified_rows),
        "auto_tp": auto_tp,
        "auto_fp": auto_fp,
        "auto_fn": auto_fn,
        "total_gold": total_gold,
        "gold_mapping_count": total_gold,
    }


def build_report(
    rows: list[dict[str, Any]],
    *,
    split: str,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    thresholds = thresholds or {}
    metrics = _aggregate(rows)
    by_schema_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_schema_rows[str(row.get("schema_id", "unknown"))].append(row)
    by_schema = {
        schema_id: _aggregate(schema_rows)
        for schema_id, schema_rows in sorted(by_schema_rows.items())
    }
    failures: list[str] = []
    warnings: list[dict[str, Any]] = []
    if metrics["auto_precision"] < thresholds.get("auto_precision", 0.0):
        failures.append("auto_precision_below_threshold")
    if metrics["auto_recall"] < thresholds.get("auto_recall", 0.0):
        failures.append("auto_recall_below_threshold")
    if metrics["review_required_rate"] > thresholds.get("review_required_rate", 1.0):
        failures.append("review_required_rate_above_threshold")
    if metrics["required_missing"]:
        failures.append("required_missing")
    if metrics["badcase_violations"]:
        failures.append("badcase_violations")
    for schema_id, schema_metrics in by_schema.items():
        if schema_metrics["required_missing"]:
            failures.append(f"{schema_id}_required_missing")
        if schema_metrics["badcase_violations"]:
            failures.append(f"{schema_id}_badcase_violations")
        if schema_metrics["gold_mapping_count"]:
            if schema_metrics["auto_precision"] < 0.85:
                warnings.append(
                    {
                        "type": "schema_precision_below_recommended_threshold",
                        "schema_id": schema_id,
                        "auto_precision": schema_metrics["auto_precision"],
                        "threshold": 0.85,
                    }
                )
            if schema_metrics["auto_recall"] < 0.85:
                warnings.append(
                    {
                        "type": "schema_recall_below_recommended_threshold",
                        "schema_id": schema_id,
                        "auto_recall": schema_metrics["auto_recall"],
                        "threshold": 0.85,
                    }
                )
    failures = sorted(set(failures))
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not failures else "failed",
        "split": split,
        "dataset_size": len(rows),
        "metrics": metrics,
        "by_schema": by_schema,
        "failures": failures,
        "warnings": warnings,
        "badcases": [
            violation
            for row in rows
            for violation in row.get("badcase_violations", [])
        ],
        "required_missing": [
            {"doc_id": row.get("doc_id"), "fields": row.get("required_missing", [])}
            for row in rows
            if row.get("required_missing")
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Topic 5 Standard UIR Mapping Evaluation",
        "",
        f"- split: {report['split']}",
        f"- status: {report['status']}",
        f"- dataset size: {report['dataset_size']}",
        f"- auto precision: {metrics['auto_precision']:.4f}",
        f"- auto recall: {metrics['auto_recall']:.4f}",
        f"- auto F1: {metrics['auto_f1']:.4f}",
        f"- assisted recall: {metrics['assisted_recall']:.4f}",
        f"- review-required rate: {metrics['review_required_rate']:.4f}",
        f"- required missing: {metrics['required_missing']}",
        f"- badcase violations: {metrics['badcase_violations']}",
        f"- conversion success rate: {metrics['conversion_success_rate']:.4f}",
        "- package verifier pass rate: "
        + (
            f"{metrics['package_verifier_pass_rate']:.4f}"
            if metrics["package_verifier_pass_rate"] is not None
            else "not run"
        ),
        f"- package verified count: {metrics['package_verified_count']}",
        "",
        "## By Schema",
        "",
        "| Schema | Docs | Auto precision | Auto recall | Review rate | Required missing | Badcases |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for schema_id, schema_metrics in report["by_schema"].items():
        lines.append(
            f"| {schema_id} | {schema_metrics['dataset_size']} | "
            f"{schema_metrics['auto_precision']:.4f} | "
            f"{schema_metrics['auto_recall']:.4f} | "
            f"{schema_metrics['review_required_rate']:.4f} | "
            f"{schema_metrics['required_missing']} | "
            f"{schema_metrics['badcase_violations']} |"
        )
    if report["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(
            f"- {warning['type']}: {warning['schema_id']}"
            for warning in report["warnings"]
        )
    return "\n".join(lines) + "\n"


def run_conversion(
    row: dict[str, Any],
    *,
    mapping_mode: str,
    verify_package: bool = False,
) -> dict[str, Any]:
    schema, template = load_schema_and_template(str(row["schema_id"]))
    options = {
        "enable_llm_fallback": False,
        "mapping_mode": mapping_mode,
        "negative_pairs": row.get("negative_pairs", []),
        "candidate_profile": row.get("candidate_profile", {}),
    }
    request = Topic5ConvertRequest.model_validate(
        {
            "uir": row["uir"],
            "target_schema": schema.model_dump(mode="json"),
            "mapping_rules": template.model_dump(mode="json"),
            "content_organization": {
                "chunk_strategy": "source_block_aware",
                "target_tokens": 1200,
                "min_tokens": 1,
                "max_tokens": 1400,
                "overlap_tokens": 0,
                "protect_tables": True,
                "protect_lists": True,
                "protect_code_blocks": True,
                "enable_parent_child": False,
                "summary_mode": "deterministic",
                "keyword_mode": "deterministic",
            },
            "options": options,
        }
    )
    with tempfile.TemporaryDirectory(prefix="topic5_eval_") as tmp:
        response = Topic5ConversionService(tmp).convert(
            request,
            create_package=verify_package,
        )
    return {
        **row,
        "mapping_report": response.mapping_report,
        "validation_passed": response.validation_report.get("passed") is True,
        "conversion_passed": response.status in {"completed", "review_required"},
        "package_verifier_passed": (
            response.verifier_report.get("passed") is True
            if verify_package and response.verifier_report
            else None
        ),
    }


def evaluate_dataset(
    dataset: Topic5EvalDataset,
    *,
    mapping_mode: str,
    verify_package: bool = False,
) -> list[dict[str, Any]]:
    converted = [
        run_conversion(
            row,
            mapping_mode=mapping_mode,
            verify_package=verify_package,
        )
        for row in dataset.items
    ]
    return evaluate_mapping_rows(
        converted,
        gold_by_doc=dataset.gold_by_doc,
        negative_pairs=dataset.negative_pairs,
        required_fields=dataset.required_fields,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--split", choices=["dev", "test", "blind", "all"], default="dev")
    parser.add_argument("--mapping-mode", choices=["legacy", "global_assignment"], default="legacy")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--fail-on-gate", action="store_true")
    parser.add_argument("--verify-package", action="store_true")
    parser.add_argument("--auto-recall-threshold", type=float, default=0.85)
    parser.add_argument("--auto-precision-threshold", type=float, default=0.90)
    parser.add_argument("--review-rate-threshold", type=float, default=0.08)
    args = parser.parse_args()

    dataset = load_dataset(args.dataset, args.split)
    rows = evaluate_dataset(
        dataset,
        mapping_mode=args.mapping_mode,
        verify_package=args.verify_package,
    )
    report = build_report(
        rows,
        split=args.split,
        thresholds={
            "auto_precision": args.auto_precision_threshold,
            "auto_recall": args.auto_recall_threshold,
            "review_required_rate": args.review_rate_threshold,
        },
    )
    report["mapping_mode"] = args.mapping_mode
    write_json(args.out, report)
    write_markdown(args.markdown, render_markdown(report))
    if args.fail_on_gate and report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
