from pathlib import Path

import pytest

from app.evaluation.mapping_evaluator import (
    evaluate_cases,
    load_eval_cases,
    score_prediction_pairs,
)

EVAL_CASES = Path(__file__).resolve().parents[2] / "examples" / "eval" / "eval_cases.json"


def test_score_prediction_pairs_reports_precision_recall_f1_and_buckets():
    report = score_prediction_pairs(
        gold_pairs={
            ("sample_1", "cand_a", "title"),
            ("sample_1", "cand_b", "owner"),
            ("sample_1", "cand_c", "date"),
        },
        predicted_pairs=[
            {
                "sample_id": "sample_1",
                "candidate_id": "cand_a",
                "target_field_id": "title",
                "confidence": 0.96,
            },
            {
                "sample_id": "sample_1",
                "candidate_id": "cand_x",
                "target_field_id": "summary",
                "confidence": 0.82,
            },
        ],
    )

    assert report["precision"] == pytest.approx(0.5)
    assert report["recall"] == pytest.approx(1 / 3)
    assert report["f1"] == pytest.approx(0.4)
    assert report["true_positive"] == 1
    assert report["false_positive"] == 1
    assert report["false_negative"] == 2
    assert report["confidence_buckets"]["[0.9,1.0]"]["accuracy"] == pytest.approx(1.0)
    assert report["confidence_buckets"]["[0.75,0.9)"]["accuracy"] == pytest.approx(0.0)


def test_evaluator_rejects_duplicate_gold_pairs():
    cases = [
        {
            "sample_id": "dup",
            "domain": "general",
            "candidates": [],
            "target_fields": [],
            "template": {},
            "gold_mappings": [
                {"candidate_id": "cand", "target_field_id": "title"},
                {"candidate_id": "cand", "target_field_id": "title"},
            ],
        }
    ]

    with pytest.raises(ValueError, match="duplicate gold mapping"):
        evaluate_cases(cases)


def test_frozen_eval_fixture_has_required_size_and_domains():
    cases = load_eval_cases(EVAL_CASES)

    assert len(cases) == 30
    assert sum(len(case["gold_mappings"]) for case in cases) == 150
    assert {case["domain"] for case in cases} == {"general", "policy", "table"}
    assert sum(
        1 for case in cases for gold in case["gold_mappings"] if gold.get("difficulty") == "hard"
    ) >= 20


def test_frozen_eval_fixture_rule_metrics_meet_phase10_thresholds():
    cases = load_eval_cases(EVAL_CASES)

    report = evaluate_cases(cases)

    assert report["sample_count"] == 30
    assert report["gold_mapping_count"] == 150
    assert report["precision"] >= 0.95
    assert report["recall"] >= 0.95
    assert report["f1"] >= 0.95
    assert report["unmapped_required_fields"] == 0
    assert report["review_required_count"] == 0
