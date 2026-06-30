import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REAL_WORLD_DIR = ROOT / "examples" / "real_world"
UIR_DIR = REAL_WORLD_DIR / "uir"
MAPPING_GOLD_PATH = REAL_WORLD_DIR / "gold" / "mapping_gold.jsonl"
SCHEMA_DIR = ROOT / "examples" / "production_like" / "schemas"

EXPECTED_DOC_TYPES = {
    "policy_doc",
    "procurement_doc",
    "meeting_doc",
    "general_doc",
}
PROCUREMENT_TARGET_FIELDS = {
    "title",
    "project_name",
    "procurement_id",
    "procurement_type",
    "purchaser",
    "agency",
    "budget_amount",
    "award_supplier",
    "award_amount",
    "announcement_date",
    "bid_deadline",
    "opening_date",
    "contact_person",
    "contact_phone",
    "source_url",
    "source_site",
    "summary",
    "content",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AssertionError(
                    f"{path}:{line_number} is not valid JSON: {exc.msg}"
                ) from exc
            assert isinstance(row, dict), f"{path}:{line_number} must contain an object"
            rows.append(row)
    return rows


def test_real_world_mapping_gold_is_valid_jsonl() -> None:
    assert MAPPING_GOLD_PATH.is_file(), f"missing mapping gold: {MAPPING_GOLD_PATH}"
    rows = load_jsonl(MAPPING_GOLD_PATH)

    uir_by_doc_id: dict[str, dict[str, Any]] = {}
    for path in UIR_DIR.rglob("*.json"):
        uir = json.loads(path.read_text(encoding="utf-8"))
        uir_by_doc_id[uir["doc_id"]] = uir

    assert len(rows) == 16
    doc_ids = [row.get("doc_id") for row in rows]
    assert len(set(doc_ids)) == 16
    assert set(doc_ids) == set(uir_by_doc_id)
    assert {row.get("doc_type") for row in rows} == EXPECTED_DOC_TYPES

    schema_fields: dict[str, set[str]] = {}
    for path in SCHEMA_DIR.glob("*.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema_fields[schema["schema_id"]] = {
            field["field_id"] for field in schema["fields"]
        }

    for row in rows:
        doc_id = row["doc_id"]
        doc_type = row["doc_type"]
        assert doc_type == uir_by_doc_id[doc_id]["metadata"]["doc_type"]
        assert row.get("schema_id")
        assert row.get("template_id")

        if doc_type == "procurement_doc":
            assert row["schema_id"] == "procurement_doc"
            assert row["template_id"] == "procurement_doc_base_v1"
            allowed_target_fields = PROCUREMENT_TARGET_FIELDS
        else:
            assert row["schema_id"] == doc_type
            allowed_target_fields = schema_fields[doc_type]

        expected_mappings = row.get("expected_mappings")
        assert isinstance(expected_mappings, list)
        assert len(expected_mappings) >= 3
        for mapping in expected_mappings:
            assert mapping.get("target_field")
            assert mapping["target_field"] in allowed_target_fields
            assert mapping.get("source_name") or mapping.get("source_path")

        expected_reviews = row.get("expected_review_required")
        assert isinstance(expected_reviews, list)
        for review in expected_reviews:
            assert review.get("reason")

        known_badcases = row.get("known_badcases")
        assert isinstance(known_badcases, list)
        assert known_badcases
