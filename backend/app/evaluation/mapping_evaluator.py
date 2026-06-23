from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.engines.mapping_engine import MappingEngine
from app.schemas.mapping import FieldCandidate
from app.schemas.mapping_template import MappingTemplate, RegexRule
from app.schemas.target_schema import TargetSchema

BUCKETS = (
    ("[0.9,1.0]", 0.9, 1.01),
    ("[0.75,0.9)", 0.75, 0.9),
    ("<0.75", float("-inf"), 0.75),
)


def load_eval_cases(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = data.get("cases") if isinstance(data, dict) else data
    if not isinstance(cases, list):
        raise ValueError("eval fixture must contain a cases list")
    return cases


def evaluate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    gold_pairs = _gold_pairs(cases)
    predictions: list[dict[str, Any]] = []
    unmapped_required_fields = 0
    review_required_count = 0

    for case in cases:
        mappings = MappingEngine().map_fields(
            task_id=case["sample_id"],
            candidates=[_candidate(case, item) for item in case["candidates"]],
            target_schema=_schema(case),
            template=_template(case),
            review_threshold=0.8,
        )
        mapped_targets = {mapping.target_field_id for mapping in mappings}
        required_targets = {
            field["field_id"] for field in case["target_fields"] if field.get("required", False)
        }
        unmapped_required_fields += len(required_targets - mapped_targets)
        review_required_count += sum(1 for mapping in mappings if mapping.need_review)
        for mapping in mappings:
            predictions.append({
                "sample_id": case["sample_id"],
                "candidate_id": mapping.candidate_id,
                "target_field_id": mapping.target_field_id,
                "confidence": mapping.confidence,
                "method": mapping.method,
            })

    report = score_prediction_pairs(gold_pairs=gold_pairs, predicted_pairs=predictions)
    report.update({
        "sample_count": len(cases),
        "gold_mapping_count": len(gold_pairs),
        "prediction_count": len(predictions),
        "unmapped_required_fields": unmapped_required_fields,
        "review_required_count": review_required_count,
        "domains": sorted({case["domain"] for case in cases}),
    })
    return report


def score_prediction_pairs(
    *,
    gold_pairs: set[tuple[str, str, str]],
    predicted_pairs: list[dict[str, Any]],
) -> dict[str, Any]:
    predicted = {
        (
            str(item["sample_id"]),
            str(item["candidate_id"]),
            str(item["target_field_id"]),
        )
        for item in predicted_pairs
    }
    true_positive = len(predicted & gold_pairs)
    false_positive = len(predicted - gold_pairs)
    false_negative = len(gold_pairs - predicted)
    precision = true_positive / len(predicted) if predicted else 0.0
    recall = true_positive / len(gold_pairs) if gold_pairs else 0.0
    f1 = _f1(precision, recall)

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "confidence_buckets": _confidence_buckets(predicted_pairs, gold_pairs),
    }


def _gold_pairs(cases: list[dict[str, Any]]) -> set[tuple[str, str, str]]:
    pairs: set[tuple[str, str, str]] = set()
    for case in cases:
        sample_id = str(case["sample_id"])
        for gold in case["gold_mappings"]:
            pair = (sample_id, str(gold["candidate_id"]), str(gold["target_field_id"]))
            if pair in pairs:
                raise ValueError(f"duplicate gold mapping: {pair}")
            pairs.add(pair)
    if not pairs:
        raise ValueError("eval fixture has no gold mappings")
    return pairs


def _confidence_buckets(
    predicted_pairs: list[dict[str, Any]],
    gold_pairs: set[tuple[str, str, str]],
) -> dict[str, dict[str, float | int]]:
    result: dict[str, dict[str, float | int]] = {}
    for label, lower, upper in BUCKETS:
        bucket = [
            item for item in predicted_pairs
            if lower <= float(item.get("confidence", 0.0)) < upper
        ]
        correct = sum(
            1 for item in bucket
            if (
                str(item["sample_id"]),
                str(item["candidate_id"]),
                str(item["target_field_id"]),
            ) in gold_pairs
        )
        result[label] = {
            "count": len(bucket),
            "correct": correct,
            "accuracy": correct / len(bucket) if bucket else 0.0,
        }
    return result


def _candidate(case: dict[str, Any], item: dict[str, Any]) -> FieldCandidate:
    return FieldCandidate(
        candidate_id=item["candidate_id"],
        task_id=case["sample_id"],
        doc_id=f"doc_{case['sample_id']}",
        source_path=item.get("source_path", f"metadata.{item['source_name']}"),
        source_name=item["source_name"],
        display_name=item.get("display_name", item["source_name"]),
        value_sample=item.get("value_sample"),
        inferred_type=item.get("inferred_type", "string"),
        source_blocks=item.get("source_blocks", []),
        confidence=item.get("confidence", 0.95),
    )


def _schema(case: dict[str, Any]) -> TargetSchema:
    schema_id = f"schema_{case['sample_id']}"
    return TargetSchema(
        schema_id=schema_id,
        name=f"Eval schema {case['sample_id']}",
        version="1.0.0",
        fields=case["target_fields"],
        json_schema={
            "type": "object",
            "required": [
                field["field_id"]
                for field in case["target_fields"]
                if field.get("required", False)
            ],
            "properties": {
                field["field_id"]: {"type": _json_type(field.get("type", "string"))}
                for field in case["target_fields"]
            },
        },
    )


def _template(case: dict[str, Any]) -> MappingTemplate:
    template_data = case.get("template", {})
    schema_id = f"schema_{case['sample_id']}"
    return MappingTemplate(
        template_id=f"template_{case['sample_id']}",
        schema_id=schema_id,
        name=f"Eval template {case['sample_id']}",
        version="1.0.0",
        aliases=template_data.get("aliases", {}),
        regex_rules=[RegexRule(**rule) for rule in template_data.get("regex_rules", [])],
        transform_rules=[],
        defaults={},
        enum_maps={},
    )


def _json_type(field_type: str) -> str:
    if field_type in {"int", "integer"}:
        return "integer"
    if field_type in {"float", "number"}:
        return "number"
    if field_type in {"bool", "boolean"}:
        return "boolean"
    return "string"


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0
