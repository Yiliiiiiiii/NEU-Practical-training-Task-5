from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAPPING_ROOT = ROOT / "eval" / "topic5_mapping_v2"


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_mapping_v2_meets_size_variety_split_and_leakage_constraints() -> None:
    module = load_script("eval_topic5_mapping_v2.py")
    dataset = module.load_dataset(MAPPING_ROOT)
    summary = module.validate_dataset(dataset)
    leakage = module.audit_leakage(dataset)

    assert summary["document_count"] >= 90
    assert summary["schema_family_count"] >= 6
    assert min(summary["documents_per_family"].values()) >= 15
    assert summary["positive_mapping_count"] >= 300
    assert summary["negative_decision_count"] >= 80
    assert summary["exact_name_positive_rate"] <= 0.25
    assert summary["test_held_out_source_rate"] >= 0.30
    assert summary["schema_held_out_test_count"] > 0
    assert set(summary["observed_variety"]) >= {
        "zh_labels",
        "en_labels",
        "abbreviations",
        "long_labels",
        "metadata_candidates",
        "key_value_blocks",
        "tables",
        "paragraph_candidates",
        "field_order_changes",
        "missing_optional_fields",
        "multiple_date_types",
        "semantic_distractors",
        "budget_vs_award_amount",
        "issuer_vs_organizer",
        "contact_vs_attendee",
        "publish_date_vs_effective_date",
    }
    field_sets = {
        tuple(field["field_id"] for field in schema["fields"])
        for schema in dataset.schemas.values()
    }
    assert len(field_sets) == 6
    assert leakage["passed"] is True
    assert leakage["violations"] == []


def test_mapping_metrics_count_only_automatic_predictions() -> None:
    module = load_script("eval_topic5_mapping_v2.py")
    gold = [
        {
            "doc_id": "d",
            "schema_id": "s",
            "source_path": "$.a",
            "target_field_id": "x",
            "required": True,
        },
        {
            "doc_id": "d",
            "schema_id": "s",
            "source_path": "$.b",
            "target_field_id": "y",
            "required": False,
        },
    ]
    predictions = [
        {
            "doc_id": "d",
            "source_path": "$.a",
            "target_field_id": "x",
            "status": "accepted",
            "need_review": False,
            "method": "alias",
        },
        {
            "doc_id": "d",
            "source_path": "$.b",
            "target_field_id": "y",
            "status": "review_required",
            "need_review": True,
            "method": "fuzzy",
        },
        {
            "doc_id": "d",
            "source_path": "$.c",
            "target_field_id": "z",
            "status": "accepted",
            "need_review": False,
            "method": "llm_fallback",
        },
    ]

    metrics = module.calculate_metrics(
        gold=gold,
        predictions=predictions,
        negative_pairs=[],
        no_match_cases=[],
        required_fields={"s": ["x"]},
    )

    assert metrics["auto_exact_field_accuracy"] == 0.5
    assert metrics["auto_precision"] == 1.0
    assert metrics["auto_recall"] == 0.5
    assert metrics["auto_f1"] == pytest.approx(2 / 3, abs=0.0001)
    assert metrics["required_present_field_recall"] == 1.0
    assert metrics["review_required_rate"] == pytest.approx(1 / 3, abs=0.0001)
    assert metrics["abstention_rate"] == 0.0


def test_mapping_v2_hashes_reports_and_cli_are_deterministic(tmp_path: Path) -> None:
    module = load_script("eval_topic5_mapping_v2.py")
    module.verify_frozen_hashes(MAPPING_ROOT)
    first = module.run_evaluation(MAPPING_ROOT, split="dev")
    second = module.run_evaluation(MAPPING_ROOT, split="dev")
    assert first == second
    assert first["dataset"]["id"] == "topic5_mapping_v2"
    assert first["dataset"]["version"] == "2.0.0"
    assert len(first["dataset"]["sha256"]) == 64
    assert first["external_blind"]["status"] == "not_run"
    assert "macro_f1_by_schema" in first["metrics"]

    invalid = tmp_path / "invalid"
    invalid.mkdir()
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "eval_topic5_mapping_v2.py"),
            "--dataset",
            str(invalid),
            "--split",
            "dev",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0


def test_mapping_builder_is_deterministic_and_matches_frozen_files(tmp_path: Path) -> None:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "build_topic5_mapping_v2_dataset.py"),
        "--output",
        str(tmp_path / "built"),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    expected = {
        path.relative_to(MAPPING_ROOT): path.read_bytes()
        for path in MAPPING_ROOT.rglob("*")
        if path.is_file()
    }
    actual = {
        path.relative_to(tmp_path / "built"): path.read_bytes()
        for path in (tmp_path / "built").rglob("*")
        if path.is_file()
    }
    assert actual == expected
    assert (tmp_path / "built.hashes.sha256").read_bytes() == (
        MAPPING_ROOT.parent / "topic5_mapping_v2.hashes.sha256"
    ).read_bytes()
    refused = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert refused.returncode != 0
    assert "--force" in refused.stderr


def test_mapping_hash_seal_reports_source_contract_and_unexpected_files(
    tmp_path: Path,
) -> None:
    module = load_script("eval_topic5_mapping_v2.py")
    module.verify_frozen_hashes(MAPPING_ROOT)
    hashes = json.loads((MAPPING_ROOT / "hashes.json").read_text(encoding="utf-8"))
    assert hashes["baseline_engine_commit"] == module.BASELINE_ENGINE_COMMIT
    assert set(hashes["report_files"]) == {
        "reports/baseline_dev.json",
        "reports/baseline_test.json",
        "reports/external_blind.json",
    }

    copied = tmp_path / "topic5_mapping_v2"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_topic5_mapping_v2_dataset.py"),
            "--output",
            str(copied),
        ],
        cwd=ROOT,
        check=True,
    )
    (copied / "unexpected.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected"):
        module.verify_frozen_hashes(copied)


@pytest.mark.parametrize(
    "leaked_value",
    [
        "NoticeHeading",
        "ＮｏｔｉｃｅＨｅａｄｉｎｇ",
        "notice-heading",
        "prefix_notice_heading_suffix",
        "noticeheadingextra",
    ],
)
def test_leakage_audit_rejects_normalized_and_substring_target_ids(leaked_value: str) -> None:
    module = load_script("eval_topic5_mapping_v2.py")
    dataset = copy.deepcopy(module.load_dataset(MAPPING_ROOT))
    doc_id = "mapv2-procurement_notice-01"
    dataset.uirs[doc_id]["blocks"][0]["attributes"]["display_hint"] = leaked_value
    leakage = module.audit_leakage(dataset)
    assert leakage["passed"] is False
    assert any("target_id" in row["kind"] for row in leakage["violations"])


def test_no_match_and_negative_pairs_are_distinct_and_meeting_contact_is_valid() -> None:
    module = load_script("eval_topic5_mapping_v2.py")
    dataset = module.load_dataset(MAPPING_ROOT)
    negative_sources = {(row["doc_id"], row["source_path"]) for row in dataset.negative_pairs}
    no_match_sources = {(row["doc_id"], row["source_path"]) for row in dataset.no_match_cases}
    assert negative_sources.isdisjoint(no_match_sources)
    for row in dataset.no_match_cases:
        if row["schema_id"] == "meeting_record":
            uir = dataset.uirs[row["doc_id"]]
            block_id = row["source_path"].split(".")[2]
            text = next(block["text"] for block in uir["blocks"] if block["block_id"] == block_id)
            assert "contact" not in text.casefold()
            assert "联系人" not in text


def test_validator_derives_variety_and_heldout_instead_of_trusting_manifest() -> None:
    module = load_script("eval_topic5_mapping_v2.py")
    dataset = copy.deepcopy(module.load_dataset(MAPPING_ROOT))
    for row in dataset.manifest:
        row["variety"] = ["fabricated"]
        row["held_out_source_or_layout"] = False
        row["schema_held_out"] = False
    summary = module.validate_dataset(dataset, verify_hashes=False)
    assert "fabricated" not in summary["observed_variety"]
    assert summary["test_held_out_source_rate"] >= 0.30
    assert summary["schema_held_out_test_count"] > 0


def test_negative_count_uses_unique_source_decisions() -> None:
    module = load_script("eval_topic5_mapping_v2.py")
    dataset = copy.deepcopy(module.load_dataset(MAPPING_ROOT))
    dataset.no_match_cases.append(copy.deepcopy(dataset.negative_pairs[0]))
    summary = module.validate_dataset(dataset, verify_hashes=False)
    assert summary["negative_decision_count"] == 180


def test_cardinality_is_compared_with_declared_gold_operation() -> None:
    module = load_script("eval_topic5_mapping_v2.py")
    gold = [
        {
            "doc_id": "d",
            "schema_id": "s",
            "source_path": "$.a",
            "target_field_id": "x",
            "required": False,
            "operation": "many_to_one",
        }
    ]
    prediction = [
        {
            "doc_id": "d",
            "source_path": "$.a",
            "target_field_id": "x",
            "status": "accepted",
            "need_review": False,
            "method": "alias",
            "operation": "many_to_one",
        }
    ]
    valid = module.calculate_metrics(
        gold=gold, predictions=prediction, negative_pairs=[], no_match_cases=[], required_fields={}
    )
    assert valid["invalid_cardinality_count"] == 0
    prediction[0]["operation"] = "one_to_one"
    invalid = module.calculate_metrics(
        gold=gold, predictions=prediction, negative_pairs=[], no_match_cases=[], required_fields={}
    )
    assert invalid["invalid_cardinality_count"] == 1


def test_schema_heldout_metric_is_derived_not_hardcoded() -> None:
    module = load_script("eval_topic5_mapping_v2.py")
    gold = [
        {
            "doc_id": "d",
            "schema_id": "novel",
            "source_path": "$.a",
            "target_field_id": "x",
            "required": False,
            "operation": "one_to_one",
        }
    ]
    prediction = [
        {
            "doc_id": "d",
            "source_path": "$.a",
            "target_field_id": "x",
            "status": "accepted",
            "need_review": False,
            "method": "alias",
            "operation": "one_to_one",
        }
    ]
    metrics = module.calculate_metrics(
        gold=gold,
        predictions=prediction,
        negative_pairs=[],
        no_match_cases=[],
        required_fields={},
        held_out_schema_ids={"novel"},
    )
    assert metrics["schema_held_out_f1"] == 1.0


def test_external_blind_runner_validates_and_evaluates_annotations(tmp_path: Path) -> None:
    annotations = tmp_path / "annotations.jsonl"
    predictions = tmp_path / "predictions.jsonl"
    output = tmp_path / "report.json"
    row = {
        "doc_id": "blind-1",
        "schema_id": "blind_schema",
        "source_path": "$.a",
        "target_field_id": "field_x",
        "required": True,
        "operation": "one_to_one",
        "annotation_origin": "independent_external_annotation",
    }
    annotations.write_text(json.dumps(row) + "\n", encoding="utf-8")
    predictions.write_text(
        json.dumps({**row, "status": "accepted", "need_review": False, "method": "alias"}) + "\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_topic5_mapping_v2_external_blind.py"),
            "--annotations",
            str(annotations),
            "--predictions",
            str(predictions),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "completed"
    assert report["metrics"]["auto_f1"] == 1.0
