"""Evaluate immutable Topic 5 tag-quality v2 labels."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "eval" / "topic5_tag_quality" / "v2"
BASELINE_ENGINE_COMMIT = "70ff30236d90a3c9de0534a8f6313e5bb559cbf5"
CORRECTION_POLICY = "create v3 with reason and before/after reports"


@dataclass
class TagV2Dataset:
    root: Path
    labels: list[dict[str, Any]]
    references: list[dict[str, Any]]
    taxonomy: dict[str, list[dict[str, str]]]
    hashes: dict[str, Any]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_dataset(root: Path) -> TagV2Dataset:
    return TagV2Dataset(
        root=root.resolve(),
        labels=load_jsonl(root / "labels.jsonl"),
        references=load_jsonl(root / "source_uir_refs.jsonl"),
        taxonomy=load_json(root / "taxonomy.json"),
        hashes=load_json(root / "manifest.json"),
    )


def verify_frozen_hashes(root: Path) -> None:
    manifest_path = root / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    seal_path = root.parent / f"{root.name}.manifest.sha256"
    if not seal_path.is_file():
        raise ValueError("frozen file drift: manifest seal is missing")
    expected_seal = seal_path.read_text(encoding="utf-8").strip()
    actual_seal = _sha256(manifest_path)
    if expected_seal != actual_seal:
        raise ValueError("frozen file drift: manifest seal")
    payload = json.loads(manifest_bytes)
    expected_names = set(payload.get("files", {}))
    actual_names = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    unexpected = sorted(actual_names - expected_names)
    missing = sorted(expected_names - actual_names)
    if unexpected:
        raise ValueError(f"frozen file drift: unexpected {unexpected[0]}")
    if missing:
        raise ValueError(f"frozen file drift: missing {missing[0]}")
    actual: dict[str, str] = {}
    for name, expected in payload["files"].items():
        path = root / name
        if not path.is_file():
            raise ValueError(f"frozen file drift: missing {name}")
        digest = _sha256(path)
        actual[name] = digest
        if digest != expected:
            raise ValueError(f"frozen file drift: {name}")
    combined = hashlib.sha256(
        "\n".join(f"{name}:{digest}" for name, digest in actual.items()).encode()
    ).hexdigest()
    if combined != payload["dataset_sha256"]:
        raise ValueError("frozen file drift: dataset SHA")
    payload_files = {
        name: digest
        for name, digest in actual.items()
        if name != "baseline_report.json"
    }
    payload_digest = hashlib.sha256(
        "\n".join(
            f"{name}:{digest}" for name, digest in payload_files.items()
        ).encode()
    ).hexdigest()
    if payload_digest != payload.get("payload_sha256"):
        raise ValueError("frozen file drift: payload SHA")


def _load_uir(reference: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / str(reference["source_path"])
    if _sha256(path) != reference["source_sha256"]:
        raise ValueError(f"source UIR drift: {reference['doc_id']}")
    return load_json(path)


def validate_dataset(dataset: TagV2Dataset) -> None:
    if dataset.hashes.get("dataset_id") != "topic5_tag_quality":
        raise ValueError("invalid manifest dataset_id")
    if dataset.hashes.get("version") != "2.0.0":
        raise ValueError("invalid manifest version")
    if dataset.hashes.get("immutable") is not True:
        raise ValueError("invalid manifest immutable flag")
    if dataset.hashes.get("correction_policy") != CORRECTION_POLICY:
        raise ValueError("invalid manifest correction policy")
    if dataset.hashes.get("baseline_engine_commit") != BASELINE_ENGINE_COMMIT:
        raise ValueError("invalid baseline engine identity")
    label_ids = [str(row.get("doc_id", "")) for row in dataset.labels]
    reference_ids = [str(row.get("doc_id", "")) for row in dataset.references]
    if len(label_ids) != len(set(label_ids)):
        raise ValueError("duplicate label doc_id")
    if len(reference_ids) != len(set(reference_ids)):
        raise ValueError("duplicate reference doc_id")
    if dataset.hashes.get("label_count") != len(dataset.labels):
        raise ValueError("manifest label_count mismatch")
    if dataset.hashes.get("source_reference_count") != len(dataset.references):
        raise ValueError("manifest source_reference_count mismatch")
    source_path = ROOT / str(dataset.hashes.get("annotation_source_path", ""))
    if not source_path.is_file():
        raise ValueError("annotation source path is missing")
    if _sha256(source_path) != dataset.hashes.get(
        "annotation_source_sha256"
    ):
        raise ValueError("annotation source SHA mismatch")
    if dataset.hashes.get("files", {}).get(
        "annotation_spec.jsonl"
    ) != dataset.hashes.get("annotation_source_sha256"):
        raise ValueError("frozen annotation/source SHA mismatch")
    references = {str(row["doc_id"]): row for row in dataset.references}
    if set(label_ids) != set(reference_ids):
        raise ValueError("label/reference doc_id mismatch")
    if len(dataset.labels) < 20:
        raise ValueError("tag v2 requires at least 20 label rows")
    for row in dataset.labels:
        doc_id = str(row.get("doc_id", ""))
        if doc_id not in references:
            raise ValueError(f"unknown source UIR: {doc_id}")
        uir = _load_uir(references[doc_id])
        if str(uir.get("doc_id")) != doc_id:
            raise ValueError(f"reference doc_id does not match UIR: {doc_id}")
        block_ids = {str(block["block_id"]) for block in uir.get("blocks", [])}
        unknown_blocks = set(map(str, row.get("source_block_ids", []))) - block_ids
        if unknown_blocks:
            raise ValueError(f"unknown block reference: {sorted(unknown_blocks)[0]}")
        for category in ("content", "management", "quality"):
            tags = row.get(f"{category}_tags")
            if not isinstance(tags, list) or not tags:
                raise ValueError(f"{doc_id}: {category}_tags must be non-empty")
            known = {str(record["tag"]) for record in dataset.taxonomy[category]}
            unknown = set(map(str, tags)) - known
            if unknown:
                raise ValueError(f"unknown {category} tag: {sorted(unknown)[0]}")
        for key, category in (
            ("management_expected_traces", "management"),
            ("quality_expected_traces", "quality"),
        ):
            traces = row.get(key)
            if not isinstance(traces, list) or not traces:
                raise ValueError(f"{doc_id}: trace records must be non-empty")
            for trace in traces:
                if set(trace) != {"tag", "rule_id", "scope"}:
                    raise ValueError(f"{doc_id}: invalid trace schema")
                if not isinstance(trace["scope"], str) or not trace["scope"].strip():
                    raise ValueError(f"{doc_id}: invalid trace scope")
                if (
                    not isinstance(trace["rule_id"], str)
                    or not trace["rule_id"].strip()
                ):
                    raise ValueError(f"{doc_id}: invalid trace rule_id")
                if trace["tag"] not in row[f"{category}_tags"]:
                    raise ValueError(f"{doc_id}: trace tag outside {category} labels")
            trace_tags = [str(trace["tag"]) for trace in traces]
            if len(trace_tags) != len(set(trace_tags)) or set(trace_tags) != set(
                map(str, row[f"{category}_tags"])
            ):
                raise ValueError(f"{doc_id}: trace coverage must be exactly one per tag")
        for field in ("semantic_rationale", "reviewer_role", "claim_boundary"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"{doc_id}: missing {field}")
    frozen_annotations = load_jsonl(dataset.root / "annotation_spec.jsonl")
    if frozen_annotations != dataset.labels:
        raise ValueError("frozen annotation_spec does not match labels")


def _old_module():
    path = ROOT / "scripts" / "eval_content_tag_quality.py"
    spec = importlib.util.spec_from_file_location("_tag_v2_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load tag runtime")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ratio(numerator: int, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def multilabel_accuracy(expected: set[str], actual: set[str]) -> float:
    """Return per-sample Jaccard accuracy for a multilabel prediction."""
    union = expected | actual
    return ratio(len(expected & actual), len(union)) if union else 1.0


def _known_runtime_tags(runtime: Any, dataset: TagV2Dataset) -> dict[str, set[str]]:
    known = {
        category: {str(record["tag"]) for record in dataset.taxonomy[category]}
        for category in ("content", "management", "quality")
    }
    for schema_id in runtime.RETRIEVAL.CATALOG:
        config = runtime.RETRIEVAL.default_options("heading_aware", schema_id)
        tag_rules = config.get("tag_rules", {})
        content = tag_rules.get("content", {})
        known["content"].update(map(str, content.get("base_tags", [])))
        known["content"].update(
            str(rule["tag"])
            for rule in content.get("rules", [])
            if isinstance(rule, dict) and rule.get("tag")
        )
        management = tag_rules.get("management", {})
        known["management"].update(map(str, management.get("static_tags", [])))
        quality = tag_rules.get("quality", {})
        known["quality"].update(
            map(str, quality.get("enabled_builtin_rules", []))
        )
    return known


def _correctness(expected: set[str], actual: set[str]) -> dict[str, Any]:
    return {
        "correct": expected == actual,
        "expected": sorted(expected),
        "actual": sorted(actual),
    }


def _trace_sets(
    chunks: list[dict[str, Any]],
) -> tuple[set[tuple[str, str, str]], set[tuple[str, str]]]:
    traces = {
        (str(trace.get("tag")), str(trace.get("rule_id")), str(trace.get("scope")))
        for chunk in chunks
        for trace in chunk.get("organization_trace", {}).get("tag_traces", [])
    }
    scopes = {(tag, scope) for tag, _, scope in traces}
    return traces, scopes


def trace_correctness(
    expected: set[tuple[str, str, str]], actual: set[tuple[str, str, str]]
) -> bool:
    return expected == actual


def scope_correctness(
    expected: set[tuple[str, str, str]], actual: set[tuple[str, str, str]]
) -> bool:
    return {(tag, scope) for tag, _, scope in expected} == {
        (tag, scope) for tag, _, scope in actual
    }


def evaluate(root: Path, *, verify_hashes: bool = True) -> dict[str, Any]:
    dataset = load_dataset(root)
    if verify_hashes:
        verify_frozen_hashes(root)
    validate_dataset(dataset)
    runtime = _old_module()
    known_tags = _known_runtime_tags(runtime, dataset)
    uirs = {str(ref["doc_id"]): _load_uir(ref) for ref in dataset.references}
    chunks = runtime.RETRIEVAL.generate_chunks_for_strategy(
        uirs, strategy="heading_aware"
    )
    content_tp = content_predicted = content_expected = unknown = 0
    content_accuracies: list[float] = []
    details: list[dict[str, Any]] = []
    management_correct: list[bool] = []
    quality_correct: list[bool] = []
    management_trace_correct: list[bool] = []
    management_scope_correct: list[bool] = []
    quality_trace_correct: list[bool] = []
    quality_scope_correct: list[bool] = []
    for label in dataset.labels:
        doc_id = str(label["doc_id"])
        relevant = runtime.relevant_chunks(
            {"source_block_ids": label["source_block_ids"]}, chunks.get(doc_id, [])
        )
        actual = {
            category: runtime._collect_tags(relevant, f"{category}_tags")
            for category in ("content", "management", "quality")
        }
        expected = {
            category: set(map(str, label[f"{category}_tags"]))
            for category in ("content", "management", "quality")
        }
        actual_traces, _ = _trace_sets(relevant)
        management_traces = {
            (str(row["tag"]), str(row["rule_id"]), str(row["scope"]))
            for row in label["management_expected_traces"]
        }
        quality_traces = {
            (str(row["tag"]), str(row["rule_id"]), str(row["scope"]))
            for row in label["quality_expected_traces"]
        }
        content_tp += len(actual["content"] & expected["content"])
        content_predicted += len(actual["content"])
        content_expected += len(expected["content"])
        content_accuracies.append(
            multilabel_accuracy(expected["content"], actual["content"])
        )
        for category in actual:
            unknown += len(actual[category] - known_tags[category])
        management_correct.append(actual["management"] == expected["management"])
        quality_correct.append(actual["quality"] == expected["quality"])
        actual_quality_traces = {
            trace for trace in actual_traces if trace[0] in actual["quality"]
        }
        categorized_trace_tags = actual["content"] | actual["management"] | actual["quality"]
        actual_management_traces = {
            trace
            for trace in actual_traces
            if trace[0] in actual["management"]
            or trace[0] not in categorized_trace_tags
        }
        management_trace_correct.append(
            trace_correctness(management_traces, actual_management_traces)
        )
        quality_trace_correct.append(
            trace_correctness(quality_traces, actual_quality_traces)
        )
        management_scope_correct.append(
            scope_correctness(management_traces, actual_management_traces)
        )
        quality_scope_correct.append(
            scope_correctness(quality_traces, actual_quality_traces)
        )
        details.append(
            {
                "doc_id": doc_id,
                "content_semantic": {
                    "expected": sorted(expected["content"]),
                    "actual": sorted(actual["content"]),
                },
                "management": _correctness(
                    expected["management"], actual["management"]
                ),
                "quality": _correctness(expected["quality"], actual["quality"]),
            }
        )
    precision = ratio(content_tp, content_predicted)
    recall = ratio(content_tp, content_expected)
    management_rate = ratio(sum(management_correct), len(management_correct))
    quality_rate = ratio(sum(quality_correct), len(quality_correct))
    management_trace_rate = ratio(
        sum(management_trace_correct), len(management_trace_correct)
    )
    management_scope_rate = ratio(
        sum(management_scope_correct), len(management_scope_correct)
    )
    quality_trace_rate = ratio(sum(quality_trace_correct), len(quality_trace_correct))
    quality_scope_rate = ratio(sum(quality_scope_correct), len(quality_scope_correct))

    def correctness(value: float) -> dict[str, Any]:
        return {"passed": value == 1.0, "rate": value}

    return {
        "status": "completed",
        "baseline_source_commit": dataset.hashes["baseline_engine_commit"],
        "dataset": {
            "id": dataset.hashes["dataset_id"],
            "version": dataset.hashes["version"],
            "sha256": dataset.hashes["payload_sha256"],
            "payload_sha256": dataset.hashes["payload_sha256"],
        },
        "sample_count": len(dataset.labels),
        "metrics": {
            "content_semantic": {
                "accuracy": (
                    sum(content_accuracies) / len(content_accuracies)
                    if content_accuracies
                    else 0.0
                ),
                "precision": precision,
                "recall": recall,
                "f1": ratio(2 * precision * recall, precision + recall),
            },
            "management_rule_correctness": correctness(management_rate),
            "management_trace_correctness": correctness(management_trace_rate),
            "management_scope_correctness": correctness(management_scope_rate),
            "quality_rule_correctness": correctness(quality_rate),
            "quality_trace_correctness": correctness(quality_trace_rate),
            "quality_scope_correctness": correctness(quality_scope_rate),
            "unknown_tag_count": unknown,
        },
        "samples": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = evaluate(args.dataset)
        output = args.output or args.dataset / "baseline_report.json"
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
