"""Validate and evaluate independently annotated external-blind mapping data."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("external blind JSONL rows must be objects")
    return rows


def load_evaluator():
    path = ROOT / "scripts" / "eval_topic5_mapping_v2.py"
    spec = importlib.util.spec_from_file_location("_mapping_v2_blind_eval", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load mapping v2 evaluator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def evaluate(annotations: Path, predictions: Path) -> dict[str, Any]:
    gold = load_jsonl(annotations)
    predicted = load_jsonl(predictions)
    required = {"doc_id", "schema_id", "source_path", "target_field_id", "operation"}
    keys: set[tuple[str, str, str]] = set()
    required_fields: dict[str, list[str]] = {}
    for row in gold:
        if not required <= set(row):
            raise ValueError("external annotation is missing required fields")
        if row.get("annotation_origin") != "independent_external_annotation":
            raise ValueError("external annotation origin is not independent")
        key = (str(row["doc_id"]), str(row["source_path"]), str(row["target_field_id"]))
        if key in keys:
            raise ValueError("duplicate external annotation decision")
        keys.add(key)
        if row.get("required") is True:
            required_fields.setdefault(str(row["schema_id"]), []).append(
                str(row["target_field_id"])
            )
    evaluator = load_evaluator()
    metrics = evaluator.calculate_metrics(
        gold=gold,
        predictions=predicted,
        negative_pairs=[],
        no_match_cases=[],
        required_fields=required_fields,
        held_out_schema_ids={str(row["schema_id"]) for row in gold},
    )
    return {
        "status": "completed",
        "annotation_count": len(gold),
        "annotation_sha256": hashlib.sha256(annotations.read_bytes()).hexdigest(),
        "prediction_sha256": hashlib.sha256(predictions.read_bytes()).hexdigest(),
        "metrics": metrics,
        "claim_boundary": "independently_supplied_external_annotations",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.annotations is None:
            report = {
                "status": "not_run",
                "reason": "independent annotations are required",
            }
        elif args.predictions is None:
            raise ValueError("--predictions is required with --annotations")
        else:
            report = evaluate(args.annotations, args.predictions)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
