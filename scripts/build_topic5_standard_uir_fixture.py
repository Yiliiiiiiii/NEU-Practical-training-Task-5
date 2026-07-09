"""Build the Topic 5 standard UIR benchmark fixture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "eval" / "topic5_standard_uir"


FAMILIES: dict[str, dict[str, Any]] = {
    "announcement_doc": {
        "prefix": "ann",
        "required": ["title", "body"],
        "fields": {
            "title": "Campus System Maintenance Announcement {n}",
            "issuer": "Information Office",
            "publish_date": "2026-07-{day:02d}",
            "body": "The campus system will be maintained during the evening window.",
        },
    },
    "event_notice_doc": {
        "prefix": "event",
        "required": ["title", "organizer", "event_time", "body"],
        "fields": {
            "title": "Network Security Lecture Notice {n}",
            "organizer": "Information Security School",
            "event_time": "2026-07-{day:02d} 14:00",
            "location": "Main Building 301",
            "audience": "All information security students",
            "body": "Please arrive ten minutes early and bring your student ID.",
        },
        "candidate_profile": {
            "labeled_values": {
                "organizer": ["organizer"],
                "event_time": ["event_time", "event time"],
                "location": ["location"],
                "audience": ["audience"],
            }
        },
    },
    "policy_doc": {
        "prefix": "policy",
        "required": ["title", "issuer", "publish_date", "content"],
        "fields": {
            "title": "Digital Service Policy {n}",
            "issuer": "City Data Bureau",
            "publish_date": "2026-07-{day:02d}",
            "content": "This policy improves digital public service handling standards.",
        },
    },
    "meeting_doc": {
        "prefix": "meeting",
        "required": ["meeting_title", "meeting_date", "content"],
        "fields": {
            "meeting_title": "Project Coordination Meeting {n}",
            "meeting_date": "2026-07-{day:02d}",
            "organizer": "Project Office",
            "content": "The meeting reviewed milestones and confirmed next actions.",
        },
    },
    "procurement_doc": {
        "prefix": "proc",
        "required": ["title", "project_name", "purchaser"],
        "fields": {
            "title": "Smart Classroom Equipment Procurement Notice {n}",
            "project_name": "Smart Classroom Equipment Upgrade {n}",
            "purchaser": "Academic Affairs Office",
            "budget_amount": "560000",
            "content": "The procurement includes display devices and classroom control terminals.",
        },
    },
    "general_doc": {
        "prefix": "general",
        "required": ["title", "content"],
        "fields": {
            "title": "Student Service Guide {n}",
            "source": "Student Affairs Office",
            "created_date": "2026-07-{day:02d}",
            "content": "This guide explains service scope, application conditions, and process steps.",
        },
    },
}


NEGATIVE_PAIRS = [
    {
        "schema_id": "event_notice_doc",
        "source_pattern": "publish date|retrieved_at",
        "target_field_id": "event_time",
        "reason": "publish or retrieved time is not event time",
        "severity": "block",
    },
    {
        "schema_id": "policy_doc",
        "source_pattern": "effective_date|retrieved_at",
        "target_field_id": "publish_date",
        "reason": "effective or retrieved time is not publish date",
        "severity": "block",
    },
    {
        "schema_id": "procurement_doc",
        "source_pattern": "budget_amount",
        "target_field_id": "award_amount",
        "reason": "budget amount is not award amount",
        "severity": "block",
    },
    {
        "schema_id": "meeting_doc",
        "source_pattern": "chairperson|host",
        "target_field_id": "attendees",
        "reason": "chairperson is not the attendee list",
        "severity": "block",
    },
    {
        "schema_id": "general_doc",
        "source_pattern": "contact",
        "target_field_id": "service_object",
        "reason": "contact details are not service object",
        "severity": "block",
    },
]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def block(block_id: str, field_id: str, text: str) -> dict[str, Any]:
    return {
        "block_id": block_id,
        "type": "heading" if field_id in {"title", "meeting_title"} else "paragraph",
        "text": text,
        "attributes": {"field_name": field_id},
    }


def build_uir(schema_id: str, index: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    family = FAMILIES[schema_id]
    prefix = family["prefix"]
    day = 9 + index
    doc_id = f"uir_{schema_id}_{index:03d}"
    blocks: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []
    for field_id, template in family["fields"].items():
        value = str(template).format(n=index, day=day)
        block_id = f"{prefix}_{index:03d}_{field_id}"
        blocks.append(block(block_id, field_id, value))
        gold.append(
            {
                "doc_id": doc_id,
                "schema_id": schema_id,
                "target_field_id": field_id,
                "source_path": f"$.blocks.{block_id}.text",
                "source_name": field_id,
                "required": field_id in family["required"],
                "match_type": "exact",
                "notes": "field_name attribute provides a standard UIR source candidate",
            }
            )

    blocks.append(
        {
            "block_id": f"{prefix}_{index:03d}_distractor",
            "type": "paragraph",
            "text": "publish date: 2026-07-01; retrieved_at: 2026-07-02T08:00:00Z",
            "attributes": {"field_name": "publish date"},
        }
    )
    uir = {
        "uir_version": "1.0",
        "doc_id": doc_id,
        "metadata": {
            "domain": schema_id,
            "source": "topic5_standard_uir_fixture",
            "language": "en-US",
        },
        "blocks": blocks,
        "assets": [],
        "normalization_records": [],
    }
    return uir, gold


def main() -> None:
    manifest: list[dict[str, Any]] = []
    gold_rows: list[dict[str, Any]] = []
    splits = {"dev": [], "test": [], "blind": []}

    for schema_id, family in FAMILIES.items():
        prefix = family["prefix"]
        for index in range(1, 11):
            uir, gold = build_uir(schema_id, index)
            filename = f"{prefix}_{index:03d}.json"
            item_key = f"{schema_id}/{filename}"
            uir_path = DATASET / "uir" / item_key
            write_json(uir_path, uir)
            manifest_row = {
                "doc_id": uir["doc_id"],
                "schema_id": schema_id,
                "family": schema_id,
                "uir_path": f"uir/{item_key}",
            }
            if family.get("candidate_profile"):
                manifest_row["candidate_profile"] = family["candidate_profile"]
            manifest.append(manifest_row)
            gold_rows.extend(gold)
            if index <= 3:
                splits["dev"].append(item_key)
            elif index <= 6:
                splits["test"].append(item_key)
            else:
                splits["blind"].append(item_key)

    write_jsonl(DATASET / "manifest.jsonl", manifest)
    for split, items in splits.items():
        write_json(DATASET / "splits" / f"{split}.json", {"split": split, "items": items})
    write_jsonl(DATASET / "gold" / "mapping_gold.jsonl", gold_rows)
    write_jsonl(DATASET / "gold" / "negative_pairs.jsonl", NEGATIVE_PAIRS)
    write_json(
        DATASET / "gold" / "required_fields.json",
        {schema_id: family["required"] for schema_id, family in FAMILIES.items()},
    )
    (DATASET / "reports").mkdir(parents=True, exist_ok=True)
    (DATASET / "reports" / ".gitkeep").write_text("", encoding="utf-8")
    (DATASET / "README.md").write_text(
        "\n".join(
            [
                "# Topic 5 Standard UIR Mapping Benchmark",
                "",
                "This coursework-scale benchmark contains 60 generated standard UIR samples.",
                "It is split by document family into dev, test, and blind partitions.",
                "",
                "Scope: standard UIR inputs, registered or inline target schemas, declared mapping rules,",
                "and benchmarked document families. It is not a production blind corpus.",
                "",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
