from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TAG_ROOT = ROOT / "eval" / "topic5_tag_quality" / "v2"
ANNOTATIONS = ROOT / "eval" / "topic5_tag_quality" / "v2_annotation_spec.jsonl"


def load_module():
    path = ROOT / "scripts" / "eval_topic5_tag_quality_v2.py"
    spec = importlib.util.spec_from_file_location("eval_topic5_tag_quality_v2", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_tag_v2_is_valid_hashed_and_separates_semantic_from_rules() -> None:
    module = load_module()
    dataset = module.load_dataset(TAG_ROOT)
    module.validate_dataset(dataset)
    module.verify_frozen_hashes(TAG_ROOT)
    report = module.evaluate(TAG_ROOT)
    assert set(report["metrics"]) == {
        "content_semantic",
        "management_rule_correctness",
        "management_trace_correctness",
        "management_scope_correctness",
        "quality_rule_correctness",
        "quality_trace_correctness",
        "quality_scope_correctness",
        "unknown_tag_count",
    }
    assert set(report["metrics"]["content_semantic"]) == {"precision", "recall", "f1"}
    assert "f1" not in report["metrics"]["management_rule_correctness"]
    assert report == module.evaluate(TAG_ROOT)


def test_tag_v2_rejects_unknown_tags_invalid_references_and_hash_drift(tmp_path: Path) -> None:
    module = load_module()
    dataset = module.load_dataset(TAG_ROOT)
    unknown = copy.deepcopy(dataset)
    unknown.labels[0]["content_tags"].append("not-in-taxonomy")
    with pytest.raises(ValueError, match="unknown content tag"):
        module.validate_dataset(unknown)
    invalid = copy.deepcopy(dataset)
    invalid.labels[0]["source_block_ids"] = ["missing-block"]
    with pytest.raises(ValueError, match="unknown block reference"):
        module.validate_dataset(invalid)
    copied = tmp_path / "v2"
    copied.mkdir()
    for path in TAG_ROOT.iterdir():
        if path.is_file():
            (copied / path.name).write_bytes(path.read_bytes())
    (copied.parent / "v2.manifest.sha256").write_bytes(
        (TAG_ROOT.parent / "v2.manifest.sha256").read_bytes()
    )
    labels = copied / "labels.jsonl"
    labels.write_text(labels.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="frozen file drift"):
        module.verify_frozen_hashes(copied)


def test_annotation_spec_is_independent_auditable_and_not_old_gold_projection() -> None:
    builder_source = (ROOT / "scripts" / "build_topic5_tag_quality_v2_dataset.py").read_text(
        encoding="utf-8"
    )
    assert "content_organization_gold" not in builder_source
    rows = [json.loads(line) for line in ANNOTATIONS.read_text(encoding="utf-8").splitlines()]
    old = {
        row["doc_id"]: row
        for row in (
            json.loads(line)
            for line in (
                ROOT / "examples" / "real_world" / "gold" / "content_organization_gold.jsonl"
            )
            .read_text(encoding="utf-8")
            .splitlines()
        )
    }
    assert all(row["semantic_rationale"] for row in rows)
    assert all(row["reviewer_role"] == "independent_dataset_annotator" for row in rows)
    assert all(row["claim_boundary"] == "public_fixture_baseline_only" for row in rows)
    assert any(row["source_block_ids"] != old[row["doc_id"]]["source_block_ids"] for row in rows)


def test_builder_refuses_overwrite_without_force_and_reproduces_freeze(tmp_path: Path) -> None:
    output = tmp_path / "v2"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "build_topic5_tag_quality_v2_dataset.py"),
        "--output",
        str(output),
    ]
    first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert first.returncode == 0, first.stderr
    refused = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert refused.returncode != 0
    assert "--force" in refused.stderr
    forced = subprocess.run(
        [*command, "--force"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert forced.returncode == 0, forced.stderr
    assert {
        path.relative_to(output): path.read_bytes() for path in output.rglob("*") if path.is_file()
    } == {
        path.relative_to(TAG_ROOT): path.read_bytes()
        for path in TAG_ROOT.rglob("*")
        if path.is_file()
    }
    assert (output.parent / "v2.manifest.sha256").read_bytes() == (
        TAG_ROOT.parent / "v2.manifest.sha256"
    ).read_bytes()


def test_manifest_rejects_unexpected_files_and_invalid_counts(tmp_path: Path) -> None:
    module = load_module()
    copied = tmp_path / "v2"
    copied.mkdir()
    for path in TAG_ROOT.iterdir():
        if path.is_file():
            (copied / path.name).write_bytes(path.read_bytes())
    (copied.parent / "v2.manifest.sha256").write_bytes(
        (TAG_ROOT.parent / "v2.manifest.sha256").read_bytes()
    )
    (copied / "unexpected.txt").write_text("drift", encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected"):
        module.verify_frozen_hashes(copied)
    dataset = module.load_dataset(TAG_ROOT)
    dataset.hashes["label_count"] += 1
    with pytest.raises(ValueError, match="label_count"):
        module.validate_dataset(dataset)


def test_manifest_seal_payload_hash_and_engine_identity_are_verified(
    tmp_path: Path,
) -> None:
    module = load_module()
    copied = tmp_path / "v2"
    copied.mkdir()
    for path in TAG_ROOT.iterdir():
        if path.is_file():
            (copied / path.name).write_bytes(path.read_bytes())
    seal = TAG_ROOT.parent / "v2.manifest.sha256"
    (copied.parent / seal.name).write_bytes(seal.read_bytes())

    manifest_path = copied / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["payload_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest seal|payload SHA"):
        module.verify_frozen_hashes(copied)

    manifest_path.write_bytes((TAG_ROOT / "manifest.json").read_bytes())
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["baseline_engine_commit"] = "deadbeef"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    dataset = module.load_dataset(copied)
    with pytest.raises(ValueError, match="baseline engine"):
        module.validate_dataset(dataset)


def test_validation_rejects_duplicates_doc_mismatch_and_bad_trace_schema() -> None:
    module = load_module()
    dataset = module.load_dataset(TAG_ROOT)
    duplicate = copy.deepcopy(dataset)
    duplicate.labels.append(copy.deepcopy(duplicate.labels[0]))
    with pytest.raises(ValueError, match="duplicate label"):
        module.validate_dataset(duplicate)
    mismatch = copy.deepcopy(dataset)
    mismatch.references[0]["doc_id"] = "wrong-doc"
    with pytest.raises(ValueError, match="reference doc_id"):
        module.validate_dataset(mismatch)
    bad_trace = copy.deepcopy(dataset)
    bad_trace.labels[0]["management_expected_traces"][0]["scope"] = ""
    with pytest.raises(ValueError, match="trace scope"):
        module.validate_dataset(bad_trace)


def test_validation_requires_exactly_one_trace_per_rule_tag(monkeypatch) -> None:
    module = load_module()
    dataset = copy.deepcopy(module.load_dataset(TAG_ROOT))
    dataset.labels[0]["management_expected_traces"] = dataset.labels[0][
        "management_expected_traces"
    ][:-1]
    original_load_jsonl = module.load_jsonl

    def load_jsonl(path):
        if Path(path).name == "annotation_spec.jsonl":
            return dataset.labels
        return original_load_jsonl(path)

    monkeypatch.setattr(module, "load_jsonl", load_jsonl)
    with pytest.raises(ValueError, match="trace coverage"):
        module.validate_dataset(dataset)


def test_evaluator_rejects_extra_unknown_runtime_trace(monkeypatch) -> None:
    module = load_module()
    original_trace_sets = module._trace_sets

    def trace_sets(chunks):
        traces, scopes = original_trace_sets(chunks)
        traces.add(("bogus-runtime-tag", "bogus-rule", "chunk"))
        scopes.add(("bogus-runtime-tag", "chunk"))
        return traces, scopes

    monkeypatch.setattr(module, "_trace_sets", trace_sets)
    report = module.evaluate(TAG_ROOT)

    assert report["metrics"]["management_trace_correctness"]["passed"] is False
    assert report["metrics"]["management_scope_correctness"]["passed"] is False


def test_trace_and_scope_correctness_reject_extra_actual_records() -> None:
    module = load_module()
    expected = {("schema:x", "schema-id", "chunk")}
    actual = expected | {("schema:y", "schema-id", "chunk")}
    assert module.trace_correctness(expected, expected) is True
    assert module.trace_correctness(expected, actual) is False
    assert module.scope_correctness(expected, actual) is False


def test_taxonomy_defines_every_tag() -> None:
    taxonomy = json.loads((TAG_ROOT / "taxonomy.json").read_text(encoding="utf-8"))
    for category in ("content", "management", "quality"):
        assert taxonomy[category]
        assert all(set(record) >= {"tag", "definition"} for record in taxonomy[category])
