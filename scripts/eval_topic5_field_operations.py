"""Evaluate the fixed Topic 5 field-operation fixture against production services."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.schemas.target_schema import TargetField  # noqa: E402
from app.schemas.transform import TransformRule  # noqa: E402
from app.schemas.uir import UIRBlock, UIRDocument  # noqa: E402
from app.services.field_operation_service import FieldOperationService  # noqa: E402

DEFAULT_FIXTURE = ROOT / "eval" / "topic5_field_operations" / "v1" / "cases.json"
DEFAULT_OUTPUT = ROOT / "docs" / "交接" / "evidence" / "hard_gap_batch_1" / "operations"
MINIMUM_COUNTS = {
    "rename": 20,
    "merge": 15,
    "split": 15,
    "conversion": 20,
    "default": 10,
    "nested_array": 10,
    "unsafe": 20,
}


def load_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "1.0.0" or not isinstance(payload.get("groups"), list):
        raise ValueError("field-operation fixture must be version 1.0.0")
    counts = {
        str(group.get("category")): len(group.get("variants", []))
        for group in payload["groups"]
    }
    for category, minimum in MINIMUM_COUNTS.items():
        if counts.get(category, 0) < minimum:
            raise ValueError(
                f"field-operation fixture requires {minimum} {category} cases"
            )
    return payload


def _base_uir(metadata: dict[str, Any], block_values: list[str] | None = None) -> UIRDocument:
    return UIRDocument(
        uir_version="1.0",
        doc_id="field-operation-eval",
        metadata=metadata,
        blocks=[
            UIRBlock(block_id=f"b{index}", type="paragraph", text=value)
            for index, value in enumerate(block_values or [], start=1)
        ],
    )


def _target(type_: str) -> TargetField:
    return TargetField(
        field_id="target",
        name="target",
        display_name="Target",
        type=type_,
    )


def evaluate_variant(group: dict[str, Any], variant: list[Any]) -> dict[str, Any]:
    category = str(group["category"])
    operation = str(group["operation"])
    target_type = str(group.get("target_type", "string"))
    metadata: dict[str, Any] = {}
    block_values: list[str] = []
    params: dict[str, Any] = {}
    current_value: Any = None
    expected_applied = True
    expected_error: str | None = None

    if category == "rename":
        case_id, source_path, expected = variant
        metadata = _metadata_for_path(source_path, expected)
        source_field = source_path
    elif category == "merge":
        case_id, block_values, separator, skip_empty, expected = variant
        source_field = None
        params = {"separator": separator, "skip_empty": skip_empty}
    elif category == "split":
        case_id, source_value, separators, expected = variant
        metadata = {"source": source_value}
        source_field = "metadata.source"
        params = {"separators": separators}
    elif category == "conversion":
        case_id, operation, target_type, source_value, params, expected = variant
        metadata = {"source": source_value}
        source_field = "metadata.source"
    elif category == "default":
        case_id, current_value, default_value, expected_applied, expected = variant
        source_field = None
        params = {"value": default_value}
    elif category == "nested_array":
        case_id, source_path, target_type, metadata, expected = variant
        source_field = source_path
    elif category == "unsafe":
        case_id, source_field, expected_error = variant
        metadata = {"owner": "value"}
        expected = None
        expected_applied = False
    else:
        raise ValueError(f"unsupported fixture category: {category}")

    source_fields = (
        [f"blocks.b{index}.text" for index in range(1, len(block_values) + 1)]
        if category == "merge"
        else []
    )
    rule = TransformRule(
        rule_id=case_id,
        operation=operation,
        source_field=source_field,
        source_fields=source_fields,
        target_field_id="target",
        params=params,
    )
    outcome = FieldOperationService().apply(
        rule=rule,
        uir=_base_uir(metadata, block_values),
        target_field=_target(target_type),
        current_value=current_value,
    )
    passed = (
        outcome.applied == expected_applied
        and outcome.value == expected
        and outcome.error == expected_error
    )
    return {
        "case_id": case_id,
        "category": category,
        "operation": operation,
        "passed": passed,
        "expected": expected,
        "actual": outcome.value,
        "expected_error": expected_error,
        "actual_error": outcome.error,
    }


def _metadata_for_path(path: str, value: Any) -> dict[str, Any]:
    parts = path.split(".")[1:]
    result: dict[str, Any] = {}
    cursor = result
    for part in parts[:-1]:
        child: dict[str, Any] = {}
        cursor[part] = child
        cursor = child
    cursor[parts[-1]] = value
    return result


def build_report(fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    fixture = load_fixture(fixture_path)
    results = [
        evaluate_variant(group, variant)
        for group in fixture["groups"]
        for variant in group["variants"]
    ]
    by_category: dict[str, dict[str, Any]] = {}
    for result in results:
        row = by_category.setdefault(result["category"], {"passed": 0, "total": 0})
        row["total"] += 1
        row["passed"] += int(result["passed"])
    for row in by_category.values():
        row["accuracy"] = row["passed"] / row["total"]
    passed_count = sum(item["passed"] for item in results)
    unsafe_operation_count = sum(
        item["category"] == "unsafe" and item["actual_error"] is None
        for item in results
    )
    fixture_bytes = fixture_path.read_bytes()
    return {
        "dataset_id": fixture["dataset_id"],
        "dataset_version": fixture["version"],
        "dataset_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "commit_sha": _commit_sha(),
        "generated_at": datetime.now(UTC).isoformat(),
        "case_count": len(results),
        "passed_count": passed_count,
        "field_operation_accuracy": passed_count / len(results),
        "rename_accuracy": by_category["rename"]["accuracy"],
        "merge_accuracy": by_category["merge"]["accuracy"],
        "split_accuracy": by_category["split"]["accuracy"],
        "conversion_accuracy": by_category["conversion"]["accuracy"],
        "unsafe_operation_count": unsafe_operation_count,
        "by_operation": by_category,
        "failed_cases": [item for item in results if not item["passed"]],
        "cases": results,
        "reproduction_command": (
            "backend/.venv/Scripts/python.exe scripts/eval_topic5_field_operations.py"
        ),
        "claim_boundary": (
            "Measures deterministic Topic 5 field operations only; it does not measure "
            "semantic extraction, retrieval, or downstream quality scoring."
        ),
    }


def _commit_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Topic 5 Field Operations",
        "",
        f"- Dataset: `{report['dataset_id']}` `{report['dataset_version']}`",
        f"- Dataset SHA-256: `{report['dataset_sha256']}`",
        f"- Commit: `{report['commit_sha']}`",
        f"- Cases: {report['case_count']}",
        f"- Accuracy: {report['field_operation_accuracy']:.3f}",
        f"- Unsafe operations accepted: {report['unsafe_operation_count']}",
        "",
        "| Category | Passed | Total | Accuracy |",
        "| --- | ---: | ---: | ---: |",
    ]
    for category, row in report["by_operation"].items():
        lines.append(
            f"| {category} | {row['passed']} | {row['total']} | {row['accuracy']:.3f} |"
        )
    lines.extend(
        [
            "",
            f"Reproduce: `{report['reproduction_command']}`",
            "",
            f"Claim boundary: {report['claim_boundary']}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(args.fixture)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "field_operations.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "field_operations.md").write_text(
        render_markdown(report), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
