from __future__ import annotations

from pathlib import Path

from scripts.eval_topic5_standard_uir_mapping import (
    build_report,
    detect_badcase_violations,
    detect_required_missing,
    evaluate_mapping_rows,
    load_dataset,
)

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "eval" / "topic5_standard_uir"


def test_eval_script_loads_dataset() -> None:
    dataset = load_dataset(DATASET, "dev")

    assert dataset.split == "dev"
    assert dataset.items
    assert dataset.gold_by_doc
    assert dataset.required_fields


def test_eval_metrics_precision_recall() -> None:
    gold_rows = [
        {
            "doc_id": "doc-1",
            "schema_id": "event_notice_doc",
            "target_field_id": "title",
            "source_path": "$.blocks.e1.text",
            "required": True,
        },
        {
            "doc_id": "doc-1",
            "schema_id": "event_notice_doc",
            "target_field_id": "event_time",
            "source_path": "$.blocks.e3.text",
            "required": True,
        },
    ]
    mapping_report = {
        "summary": {"total_target_fields": 4},
        "mappings": [
            {
                "target_field_id": "title",
                "source_path": "$.blocks.e1.text",
                "status": "accepted",
            },
            {
                "target_field_id": "event_time",
                "source_path": "$.blocks.wrong.text",
                "status": "accepted",
            },
        ],
        "review_required_items": [],
        "unmapped": [],
    }

    rows = evaluate_mapping_rows(
        [
            {
                "doc_id": "doc-1",
                "schema_id": "event_notice_doc",
                "mapping_report": mapping_report,
                "package_passed": True,
            }
        ],
        gold_by_doc={"doc-1": gold_rows},
        negative_pairs=[],
        required_fields={"event_notice_doc": ["title", "event_time"]},
    )
    report = build_report(rows, split="dev")

    assert report["metrics"]["auto_precision"] == 0.5
    assert report["metrics"]["auto_recall"] == 0.5
    assert report["metrics"]["auto_f1"] == 0.5


def test_badcase_violation_detection() -> None:
    violations = detect_badcase_violations(
        {
            "mappings": [
                {
                    "target_field_id": "event_time",
                    "source_field": {"source_name": "publish date"},
                    "status": "accepted",
                }
            ]
        },
        [
            {
                "schema_id": "event_notice_doc",
                "source_pattern": "publish date|retrieved_at",
                "target_field_id": "event_time",
                "reason": "publish or retrieved time is not event time",
                "severity": "block",
            }
        ],
        schema_id="event_notice_doc",
        doc_id="doc-1",
    )

    assert violations == [
        {
            "doc_id": "doc-1",
            "schema_id": "event_notice_doc",
            "target_field_id": "event_time",
            "source_name": "publish date",
            "source_path": None,
            "reason": "publish or retrieved time is not event time",
            "severity": "block",
        }
    ]


def test_required_missing_detection() -> None:
    missing = detect_required_missing(
        {"mappings": [], "review_required_items": []},
        schema_id="event_notice_doc",
        required_fields={"event_notice_doc": ["title", "organizer"]},
    )

    assert missing == ["organizer", "title"]
