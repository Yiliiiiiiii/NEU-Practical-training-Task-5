"""Validate and evaluate the frozen Topic 5 mapping-v2 benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "eval" / "topic5_mapping_v2"
DEFAULT_CALIBRATION = (
    ROOT / "eval" / "topic5_mapping_engine_v2" / "calibration.json"
)
DEFAULT_REPORT_DIR = ROOT / "eval" / "topic5_mapping_engine_v2" / "reports"
BASELINE_ENGINE_COMMIT = "70ff30236d90a3c9de0534a8f6313e5bb559cbf5"


@dataclass(frozen=True)
class MappingV2Dataset:
    root: Path
    manifest: list[dict[str, Any]]
    uirs: dict[str, dict[str, Any]]
    schemas: dict[str, dict[str, Any]]
    rules: dict[str, dict[str, Any]]
    gold: dict[str, list[dict[str, Any]]]
    negative_pairs: list[dict[str, Any]]
    no_match_cases: list[dict[str, Any]]
    required_fields: dict[str, list[str]]
    splits: dict[str, list[str]]
    hashes: dict[str, Any]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: expected JSON object")
        rows.append(value)
    return rows


def load_dataset(root: Path) -> MappingV2Dataset:
    root = root.resolve()
    manifest = load_jsonl(root / "manifest.jsonl")
    schemas = {
        path.stem: load_json(path)
        for path in sorted((root / "target_schemas").glob("*.json"))
    }
    rules = {
        path.stem: load_json(path)
        for path in sorted((root / "mapping_rules").glob("*.json"))
    }
    return MappingV2Dataset(
        root=root,
        manifest=manifest,
        uirs={
            str(row["doc_id"]): load_json(root / str(row["uir_path"]))
            for row in manifest
        },
        schemas=schemas,
        rules=rules,
        gold={
            split: load_jsonl(root / "gold" / f"{split}.jsonl")
            for split in ("dev", "test")
        },
        negative_pairs=load_jsonl(root / "gold" / "negative_pairs.jsonl"),
        no_match_cases=load_jsonl(root / "gold" / "no_match_cases.jsonl"),
        required_fields=load_json(root / "gold" / "required_fields.json"),
        splits={
            split: list(load_json(root / "splits" / f"{split}.json")["doc_ids"])
            for split in ("dev", "test")
        },
        hashes=load_json(root / "hashes.json"),
    )


def verify_frozen_hashes(root: Path) -> None:
    hashes_path = root / "hashes.json"
    hashes_bytes = hashes_path.read_bytes()
    seal_path = root.parent / f"{root.name}.hashes.sha256"
    if not seal_path.is_file():
        raise ValueError("frozen file drift: hashes seal is missing")
    if seal_path.read_text(encoding="utf-8").strip() != hashlib.sha256(
        hashes_bytes
    ).hexdigest():
        raise ValueError("frozen file drift: hashes seal")
    payload = json.loads(hashes_bytes)
    expected_names = set(payload.get("files", {})) | set(
        payload.get("report_files", {})
    )
    actual_names = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "hashes.json"
    }
    if actual_names - expected_names:
        raise ValueError(
            f"frozen file drift: unexpected {sorted(actual_names - expected_names)[0]}"
        )
    if expected_names - actual_names:
        raise ValueError(
            f"frozen file drift: missing {sorted(expected_names - actual_names)[0]}"
        )
    actual: dict[str, str] = {}
    for name, expected in payload.get("files", {}).items():
        path = root / name
        if not path.is_file():
            raise ValueError(f"frozen file drift: missing {name}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        actual[name] = digest
        if digest != expected:
            raise ValueError(f"frozen file drift: {name}")
    dataset_sha = hashlib.sha256(
        "\n".join(f"{name}:{digest}" for name, digest in actual.items()).encode()
    ).hexdigest()
    if dataset_sha != payload.get("dataset_sha256"):
        raise ValueError("frozen file drift: dataset SHA")
    for name, expected in payload.get("report_files", {}).items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"frozen file drift: {name}")
    source_root = ROOT / str(payload.get("source_path", ""))
    source_files = {
        path.relative_to(source_root).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(source_root.rglob("*"))
        if path.is_file()
    }
    source_digest = hashlib.sha256(
        "\n".join(
            f"{name}:{digest}" for name, digest in source_files.items()
        ).encode()
    ).hexdigest()
    if source_digest != payload.get("source_contract_sha256"):
        raise ValueError("frozen file drift: authored source contract")


def audit_leakage(dataset: MappingV2Dataset) -> dict[str, Any]:
    def normalized(value: Any) -> str:
        normalized_value = unicodedata.normalize("NFKC", str(value)).casefold()
        return "".join(char for char in normalized_value if char.isalnum())

    def leaks(value: Any, target_id: str) -> bool:
        candidate = normalized(value)
        target = normalized(target_id)
        return bool(
            candidate and target and (candidate in target or target in candidate)
        )

    def candidate_strings(value: Any) -> list[str]:
        if isinstance(value, dict):
            return [str(key) for key in value] + [
                item for nested in value.values() for item in candidate_strings(nested)
            ]
        if isinstance(value, list):
            return [item for nested in value for item in candidate_strings(nested)]
        return [str(value)] if isinstance(value, str) else []

    violations: list[dict[str, str]] = []
    gold_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in dataset.gold["dev"] + dataset.gold["test"]:
        gold_by_doc[str(row["doc_id"])].append(row)
    for manifest in dataset.manifest:
        doc_id = str(manifest["doc_id"])
        uir = dataset.uirs[doc_id]
        target_ids = {str(row["target_field_id"]) for row in gold_by_doc[doc_id]}
        if any(leaks(doc_id, target_id) for target_id in target_ids):
            violations.append({"doc_id": doc_id, "kind": "target_id_in_doc_id"})
        for value in uir.get("metadata", {}).keys():
            if any(leaks(value, target_id) for target_id in target_ids):
                violations.append(
                    {"doc_id": doc_id, "kind": "target_id_in_metadata_candidate"}
                )
        for block in uir.get("blocks", []):
            for value in candidate_strings(block.get("attributes", {})):
                if any(leaks(value, target_id) for target_id in target_ids):
                    violations.append(
                        {"doc_id": doc_id, "kind": "target_id_in_candidate_attribute"}
                    )
    return {"passed": not violations, "violations": violations}


def validate_dataset(
    dataset: MappingV2Dataset, *, verify_hashes: bool = True
) -> dict[str, Any]:
    if verify_hashes:
        verify_frozen_hashes(dataset.root)
    if dataset.hashes.get("dataset_id") != "topic5_mapping_v2":
        raise ValueError("invalid dataset id")
    if dataset.hashes.get("version") != "2.0.0":
        raise ValueError("invalid dataset version")
    if dataset.hashes.get("baseline_engine_commit") != BASELINE_ENGINE_COMMIT:
        raise ValueError("invalid baseline engine identity")
    if len(dataset.manifest) != len(
        {str(row.get("doc_id")) for row in dataset.manifest}
    ):
        raise ValueError("duplicate manifest doc_id")
    manifest_docs = {str(row["doc_id"]) for row in dataset.manifest}
    if set(dataset.splits["dev"]) & set(dataset.splits["test"]):
        raise ValueError("split overlap")
    if set(dataset.splits["dev"] + dataset.splits["test"]) != manifest_docs:
        raise ValueError("splits do not cover manifest")
    family_counts = Counter(str(row["family"]) for row in dataset.manifest)
    positives = dataset.gold["dev"] + dataset.gold["test"]
    for row in positives:
        if str(row.get("doc_id")) not in manifest_docs:
            raise ValueError("gold references unknown document")
        if row.get("annotation_origin") != "independent_frozen_author_label":
            raise ValueError("gold annotation origin is not independent")
        if row.get("operation") not in {"one_to_one", "one_to_many", "many_to_one"}:
            raise ValueError("gold mapping has invalid cardinality operation")
    for row in dataset.negative_pairs:
        schema_fields = {
            str(field["field_id"])
            for field in dataset.schemas[str(row["schema_id"])]["fields"]
        }
        if str(row["target_field_id"]) not in schema_fields:
            raise ValueError("negative pair references unknown target field")
    def normalize(value: Any) -> str:
        normalized_value = unicodedata.normalize("NFKC", str(value)).casefold()
        return "".join(char for char in normalized_value if char.isalnum())
    exact_count = sum(
        1
        for row in positives
        if normalize(row.get("source_label", ""))
        == normalize(row.get("target_field_id", ""))
    )
    dev_rows = [row for row in dataset.manifest if row.get("split") == "dev"]
    test_rows = [row for row in dataset.manifest if row.get("split") == "test"]

    def organization(row: dict[str, Any]) -> str:
        return str(
            dataset.uirs[str(row["doc_id"])]
            .get("metadata", {})
            .get("source_organization", "")
        )

    def layout(row: dict[str, Any]) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    str(block.get("type"))
                    for block in dataset.uirs[str(row["doc_id"])].get("blocks", [])
                    if block.get("attributes", {}).get("benchmark_role") == "source"
                }
            )
        )

    dev_organizations = {organization(row) for row in dev_rows}
    dev_layouts = {layout(row) for row in dev_rows}
    held_out_test = [
        row
        for row in test_rows
        if organization(row) not in dev_organizations or layout(row) not in dev_layouts
    ]
    dev_schemas = {str(row["schema_id"]) for row in dev_rows}
    schema_held_out_test = [
        row for row in test_rows if str(row["schema_id"]) not in dev_schemas
    ]
    observed: set[str] = set()
    labels = [str(row.get("source_label", "")) for row in positives]
    if any(re.search(r"[\u3400-\u9fff]", label) for label in labels):
        observed.add("zh_labels")
    if any(re.search(r"[A-Za-z]", label) for label in labels):
        observed.add("en_labels")
    if any("." in label or len(label) <= 8 for label in labels):
        observed.add("abbreviations")
    if any(len(label) >= 35 for label in labels):
        observed.add("long_labels")
    if any(str(row["source_path"]).startswith("$.metadata.") for row in positives):
        observed.add("metadata_candidates")
    block_types = {
        str(block.get("type"))
        for uir in dataset.uirs.values()
        for block in uir.get("blocks", [])
        if block.get("attributes", {}).get("benchmark_role") == "source"
    }
    if "key_value" in block_types:
        observed.add("key_value_blocks")
    if "table" in block_types:
        observed.add("tables")
    if "paragraph" in block_types:
        observed.add("paragraph_candidates")
    sequences: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    for split in ("dev", "test"):
        by_doc: dict[str, list[str]] = defaultdict(list)
        for row in dataset.gold[split]:
            by_doc[str(row["doc_id"])].append(str(row["target_field_id"]))
        for doc_id, sequence in by_doc.items():
            family = next(
                str(row["family"])
                for row in dataset.manifest
                if row["doc_id"] == doc_id
            )
            sequences[family].add(tuple(sequence))
    if any(len(items) > 1 for items in sequences.values()):
        observed.add("field_order_changes")
    if any(
        len(
            {
                str(row["target_field_id"])
                for row in positives
                if row["doc_id"] == doc_id
            }
        )
        < len(dataset.schemas[str(manifest["schema_id"])]["fields"])
        for doc_id, manifest in ((str(row["doc_id"]), row) for row in dataset.manifest)
    ):
        observed.add("missing_optional_fields")
    schema_types = {
        schema_id: {
            str(field["field_id"]): str(field["type"]) for field in schema["fields"]
        }
        for schema_id, schema in dataset.schemas.items()
    }
    if any(
        sum(
            schema_types[str(row["schema_id"])].get(str(row["target_field_id"]))
            == "date"
            for row in positives
            if row["doc_id"] == doc_id
        )
        >= 2
        for doc_id in manifest_docs
    ):
        observed.add("multiple_date_types")
    negative_reasons = " ".join(
        str(row.get("reason", "")) for row in dataset.negative_pairs
    )
    semantic_markers = {
        "budget_vs_award_amount": ("budget", "award"),
        "issuer_vs_organizer": ("organizer", "issuer"),
        "contact_vs_attendee": ("contact", "attendee"),
    }
    for marker, words in semantic_markers.items():
        if all(word in negative_reasons for word in words):
            observed.add(marker)
    policy_fields = set(schema_types.get("policy_release", {}))
    if {"publish_date", "effective_date"} <= policy_fields:
        observed.add("publish_date_vs_effective_date")
    if dataset.negative_pairs:
        observed.add("semantic_distractors")
    negative_source_keys = {
        (str(row["doc_id"]), str(row["source_path"])) for row in dataset.negative_pairs
    }
    no_match_source_keys = {
        (str(row["doc_id"]), str(row["source_path"])) for row in dataset.no_match_cases
    }
    unique_negative_decisions = negative_source_keys | no_match_source_keys
    summary = {
        "document_count": len(dataset.manifest),
        "schema_family_count": len(family_counts),
        "documents_per_family": dict(sorted(family_counts.items())),
        "positive_mapping_count": len(positives),
        "negative_decision_count": len(unique_negative_decisions),
        "exact_name_positive_rate": ratio(exact_count, len(positives)),
        "test_held_out_source_rate": ratio(len(held_out_test), len(test_rows)),
        "schema_held_out_test_count": len(schema_held_out_test),
        "observed_variety": sorted(observed),
    }
    minimums = {
        "document_count": 90,
        "schema_family_count": 6,
        "positive_mapping_count": 300,
        "negative_decision_count": 80,
    }
    for key, minimum in minimums.items():
        if int(summary[key]) < minimum:
            raise ValueError(f"dataset constraint failed: {key}")
    if min(family_counts.values(), default=0) < 15:
        raise ValueError("dataset constraint failed: documents_per_family")
    if float(summary["exact_name_positive_rate"]) > 0.25:
        raise ValueError("dataset constraint failed: exact-name rate")
    if float(summary["test_held_out_source_rate"]) < 0.30:
        raise ValueError("dataset constraint failed: held-out source rate")
    if int(summary["schema_held_out_test_count"]) == 0:
        raise ValueError("dataset constraint failed: schema-held-out subset")
    leakage = audit_leakage(dataset)
    if not leakage["passed"]:
        raise ValueError(
            f"dataset leakage detected: {leakage['violations'][0]['kind']}"
        )
    return summary


def ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def calculate_metrics(
    *,
    gold: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    negative_pairs: list[dict[str, Any]],
    no_match_cases: list[dict[str, Any]],
    required_fields: dict[str, list[str]],
    held_out_schema_ids: set[str] | None = None,
) -> dict[str, Any]:
    held_out_schema_ids = held_out_schema_ids or set()
    automatic = [
        row
        for row in predictions
        if row.get("status") == "accepted"
        and row.get("need_review") is False
        and row.get("method") != "llm_fallback"
    ]
    reviews = [
        row
        for row in predictions
        if row.get("need_review") is True or row.get("status") == "review_required"
    ]
    gold_keys = {
        (str(row["doc_id"]), str(row["source_path"]), str(row["target_field_id"]))
        for row in gold
    }
    auto_keys = {
        (str(row["doc_id"]), str(row["source_path"]), str(row["target_field_id"]))
        for row in automatic
    }
    tp = len(gold_keys & auto_keys)
    fp = len(auto_keys - gold_keys)
    fn = len(gold_keys - auto_keys)
    precision = ratio(tp, tp + fp)
    recall = ratio(tp, tp + fn)
    schemas = sorted({str(row["schema_id"]) for row in gold})
    schema_f1: dict[str, float] = {}
    for schema in schemas:
        schema_gold = {
            key
            for key in gold_keys
            if any(
                str(row["schema_id"]) == schema and str(row["doc_id"]) == key[0]
                for row in gold
            )
        }
        schema_auto = {
            key
            for key in auto_keys
            if key[0]
            in {str(row["doc_id"]) for row in gold if str(row["schema_id"]) == schema}
        }
        stp = len(schema_gold & schema_auto)
        sp = ratio(stp, len(schema_auto))
        sr = ratio(stp, len(schema_gold))
        schema_f1[schema] = ratio(2 * sp * sr, sp + sr)
    required_gold = [
        row
        for row in gold
        if str(row["target_field_id"]) in required_fields.get(str(row["schema_id"]), [])
    ]
    required_keys = {
        (str(row["doc_id"]), str(row["source_path"]), str(row["target_field_id"]))
        for row in required_gold
    }
    negative_keys = {
        (str(row["doc_id"]), str(row["source_path"]), str(row["target_field_id"]))
        for row in negative_pairs
    }
    no_match_keys = {
        (str(row["doc_id"]), str(row["source_path"])) for row in no_match_cases
    }
    source_counts = Counter(
        (str(row["doc_id"]), str(row["source_path"])) for row in automatic
    )
    docs = {str(row["doc_id"]) for row in gold}
    held_out_docs = {
        str(row["doc_id"])
        for row in gold
        if str(row["schema_id"]) in held_out_schema_ids
    }
    held_gold = {key for key in gold_keys if key[0] in held_out_docs}
    held_auto = {key for key in auto_keys if key[0] in held_out_docs}
    htp = len(held_gold & held_auto)
    hp = ratio(htp, len(held_auto))
    hr = ratio(htp, len(held_gold))
    return {
        "auto_exact_field_accuracy": ratio(tp, len(gold_keys)),
        "auto_precision": precision,
        "auto_recall": recall,
        "auto_f1": ratio(2 * precision * recall, precision + recall),
        "macro_f1_by_schema": ratio(sum(schema_f1.values()), len(schema_f1)),
        "per_schema_f1": schema_f1,
        "required_present_field_recall": ratio(
            len(required_keys & auto_keys), len(required_keys)
        ),
        "review_required_rate": ratio(len(reviews), len(predictions)),
        "abstention_rate": ratio(
            sum(1 for row in predictions if row.get("status") == "abstained"),
            len(predictions),
        ),
        "negative_pair_violation_count": len(auto_keys & negative_keys)
        + sum(
            1
            for row in automatic
            if (str(row["doc_id"]), str(row["source_path"])) in no_match_keys
        ),
        "duplicate_source_violation_count": sum(
            count - 1 for count in source_counts.values() if count > 1
        ),
        "invalid_cardinality_count": sum(
            1
            for row in automatic
            if row.get("operation", "one_to_one")
            != next(
                (
                    gold_row.get("operation", "one_to_one")
                    for gold_row in gold
                    if str(gold_row["doc_id"]) == str(row["doc_id"])
                    and str(gold_row["source_path"]) == str(row["source_path"])
                    and str(gold_row["target_field_id"]) == str(row["target_field_id"])
                ),
                "one_to_one",
            )
        ),
        "schema_held_out_f1": ratio(2 * hp * hr, hp + hr),
        "document_count": len(docs),
    }


def current_engine_predictions(
    dataset: MappingV2Dataset,
    split: str,
    *,
    calibration: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    backend = ROOT / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    from app.schemas.mapping_template import MappingTemplate
    from app.schemas.target_schema import TargetSchema
    from app.schemas.uir import UIRDocument
    from app.services.candidate_service import CandidateService
    from app.services.mapping_service import MappingService

    predictions: list[dict[str, Any]] = []
    manifest = {str(row["doc_id"]): row for row in dataset.manifest}
    negatives_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in dataset.negative_pairs:
        negatives_by_doc[str(row["doc_id"])].append(row)
    for doc_id in dataset.splits[split]:
        row = manifest[doc_id]
        schema_id = str(row["schema_id"])
        uir = UIRDocument.model_validate(dataset.uirs[doc_id])
        candidates = CandidateService().extract_candidates(
            doc_id, uir, enable_legacy_domain_rules=False
        )
        report = (
            MappingService()
            .map_fields(
                doc_id,
                uir,
                TargetSchema.model_validate(dataset.schemas[schema_id]),
                MappingTemplate.model_validate(dataset.rules[schema_id]),
                candidates,
                {
                    "mapping_mode": "global_assignment",
                    "enable_llm_fallback": False,
                    "negative_pairs": negatives_by_doc[doc_id],
                    "calibration": calibration,
                },
            )
            .model_dump(mode="json")
        )
        for mapping in report.get("mappings", []) + report.get("review_required", []):
            source = mapping.get("source_field", {})
            predictions.append(
                {
                    "doc_id": doc_id,
                    "source_path": source.get("source_path"),
                    "target_field_id": mapping.get("target_field_id"),
                    "status": mapping.get("status"),
                    "need_review": mapping.get("need_review"),
                    "method": mapping.get("method"),
                    "operation": mapping.get("operation") or "one_to_one",
                }
            )
        for unmapped in report.get("unmapped", []):
            predictions.append(
                {
                    "doc_id": doc_id,
                    "source_path": None,
                    "target_field_id": unmapped.get("target_field_id"),
                    "status": "abstained",
                    "need_review": False,
                    "method": "none",
                    "operation": "one_to_one",
                }
            )
    return predictions


def run_evaluation(
    root: Path, *, split: str, commit_sha: str | None = None
) -> dict[str, Any]:
    dataset = load_dataset(root)
    validation = validate_dataset(dataset)
    calibration = load_json(DEFAULT_CALIBRATION)
    if calibration.get("fit_split") != "dev":
        raise ValueError("mapping calibration was not fit on dev")
    if calibration.get("test_labels_used_for_fit") is not False:
        raise ValueError("mapping calibration used test labels during fitting")
    if calibration.get("dataset_sha256") != dataset.hashes.get("dataset_sha256"):
        raise ValueError("mapping calibration dataset identity mismatch")
    predictions = current_engine_predictions(
        dataset, split, calibration=calibration
    )
    dev_schema_ids = {
        str(row["schema_id"]) for row in dataset.manifest if row.get("split") == "dev"
    }
    test_schema_ids = {
        str(row["schema_id"]) for row in dataset.manifest if row.get("split") == "test"
    }
    held_out_schema_ids = test_schema_ids - dev_schema_ids
    metrics = calculate_metrics(
        gold=dataset.gold[split],
        predictions=predictions,
        negative_pairs=[
            row
            for row in dataset.negative_pairs
            if str(row["doc_id"]) in set(dataset.splits[split])
        ],
        no_match_cases=[
            row
            for row in dataset.no_match_cases
            if str(row["doc_id"]) in set(dataset.splits[split])
        ],
        required_fields=dataset.required_fields,
        held_out_schema_ids=held_out_schema_ids,
    )
    if split == "test":
        dev = calculate_metrics(
            gold=dataset.gold["dev"],
            predictions=current_engine_predictions(
                dataset, "dev", calibration=calibration
            ),
            negative_pairs=dataset.negative_pairs,
            no_match_cases=dataset.no_match_cases,
            required_fields=dataset.required_fields,
            held_out_schema_ids=held_out_schema_ids,
        )
        metrics["test_vs_dev_gap"] = dev["auto_f1"] - metrics["auto_f1"]
    else:
        metrics["test_vs_dev_gap"] = None
    targets = {
        "auto_exact_field_accuracy": 0.85,
        "auto_precision": 0.90,
        "auto_recall": 0.85,
        "auto_f1": 0.87,
        "macro_f1_by_schema": 0.82,
        "required_present_field_recall": 0.95,
        "review_required_rate_max": 0.20,
    }
    passed = (
        metrics["auto_exact_field_accuracy"] >= targets["auto_exact_field_accuracy"]
        and metrics["auto_precision"] >= targets["auto_precision"]
        and metrics["auto_recall"] >= targets["auto_recall"]
        and metrics["auto_f1"] >= targets["auto_f1"]
        and metrics["macro_f1_by_schema"] >= targets["macro_f1_by_schema"]
        and metrics["required_present_field_recall"]
        >= targets["required_present_field_recall"]
        and metrics["review_required_rate"] <= targets["review_required_rate_max"]
        and metrics["negative_pair_violation_count"] == 0
        and metrics["duplicate_source_violation_count"] == 0
        and metrics["invalid_cardinality_count"] == 0
    )
    return {
        "status": "passed" if passed else "failed",
        "commit_sha": commit_sha or git_head(),
        "baseline_source_commit": dataset.hashes["baseline_engine_commit"],
        "split": split,
        "dataset": {
            "id": dataset.hashes["dataset_id"],
            "version": dataset.hashes["version"],
            "sha256": dataset.hashes["dataset_sha256"],
            "group_hashes": dataset.hashes["groups"],
        },
        "validation": validation,
        "engine": {
            "name": "mapping_engine_v2",
            "mapping_mode": "global_assignment",
            "assignment_algorithm": "maximum_weight_bipartite",
            "llm_fallback": False,
            "calibration_artifact": str(DEFAULT_CALIBRATION.relative_to(ROOT)),
            "calibration_method": calibration["method"],
            "calibration_fit_split": calibration["fit_split"],
            "calibration_fit_engine_commit": calibration["fit_engine_commit"],
            "thresholds": calibration["thresholds"],
            "brier_score": calibration["brier_score"],
            "expected_calibration_error": calibration[
                "expected_calibration_error"
            ],
            "reliability_bins": calibration["reliability_bins"],
            "precision_coverage_curve": calibration[
                "precision_coverage_curve"
            ],
        },
        "metrics": metrics,
        "targets": targets,
        "external_blind": {
            "status": "not_run",
            "reason": "independent annotations are not available",
        },
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--split", choices=("dev", "test"), required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--commit-sha")
    parser.add_argument("--fail-on-targets", action="store_true")
    args = parser.parse_args()
    try:
        report = run_evaluation(
            args.dataset, split=args.split, commit_sha=args.commit_sha
        )
        output = args.output or DEFAULT_REPORT_DIR / f"{args.split}.json"
        write_json(output, report)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    if args.fail_on_targets and report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
