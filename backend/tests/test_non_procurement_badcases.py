import json
from pathlib import Path

from app.schemas.mapping import FieldCandidate
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.uir import UIRDocument
from app.services.mapping_service import MappingService

ROOT = Path(__file__).resolve().parents[2]
BADCASES = ROOT / "examples" / "real_world" / "gold" / "real_world_badcases.jsonl"
SCHEMAS_DIR = ROOT / "examples" / "production_like" / "schemas"

REQUIRED_CONFUSION_PAIRS = {
    ("发布日期", "effective_date"),
    ("主持人", "attendees"),
    ("联系人", "attendees"),
    ("承办单位", "issuer"),
    ("预算金额", "award_amount"),
    ("控制价", "award_amount"),
}


def load_badcases() -> list[dict]:
    return [
        json.loads(line)
        for line in BADCASES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_required_non_procurement_confusion_pairs_exist() -> None:
    rows = load_badcases()
    pairs = {
        (
            row["forbidden_auto_mapping"]["source_name"],
            row["forbidden_auto_mapping"]["target_field"],
        )
        for row in rows
    }

    assert REQUIRED_CONFUSION_PAIRS <= pairs


def test_badcase_rows_have_evidence_and_required_contract() -> None:
    rows = load_badcases()
    required_rows = [
        row
        for row in rows
        if (
            row["forbidden_auto_mapping"]["source_name"],
            row["forbidden_auto_mapping"]["target_field"],
        )
        in REQUIRED_CONFUSION_PAIRS
    ]

    assert len(required_rows) == len(REQUIRED_CONFUSION_PAIRS)
    for row in required_rows:
        assert set(row) >= {
            "case_id",
            "doc_id",
            "badcase_type",
            "source_evidence",
            "forbidden_auto_mapping",
            "expected_behavior",
            "severity",
        }
        assert row["source_evidence"]["source_paths"]
        assert row["source_evidence"]["excerpt"]


def test_badcase_pair_cannot_be_auto_accepted() -> None:
    policy_uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "policy-badcase",
            "metadata": {},
            "blocks": [{"block_id": "b1", "type": "paragraph", "text": "发布日期：2026-07-01"}],
            "assets": [],
            "normalization_records": [],
        }
    )
    candidate = FieldCandidate(
        candidate_id="cand_bad_date",
        task_id="task_bad_date",
        doc_id=policy_uir.doc_id,
        source_path="$.blocks.b1.text",
        source_name="发布日期",
        value_sample="2026-07-01",
        inferred_type="date",
        source_blocks=["b1"],
        confidence=0.99,
        evidence=["explicit label"],
    )

    schema = TargetSchema(
        schema_id="policy_doc",
        name="Policy Badcase Probe",
        version="1.0.0",
        fields=[
            TargetField(
                field_id="effective_date",
                name="effective_date",
                display_name="生效日期",
                type="date",
                required=False,
            )
        ],
    )
    template = MappingTemplate(
        template_id="policy_doc_base_v1",
        schema_id="policy_doc",
        name="Policy Badcase Probe",
        version="1.0.0",
        aliases={"effective_date": ["发布日期"]},
    )

    report = MappingService().map_fields(
        task_id="task_bad_date",
        uir=policy_uir,
        schema=schema,
        template=template,
        candidates=[candidate],
        options={
            "badcases": [
                {
                    "source_field": "发布日期",
                    "forbidden_target_fields": ["effective_date"],
                }
            ]
        },
    )

    assert all(
        not (item["target_field_id"] == "effective_date" and item["status"] == "accepted")
        for item in report.mappings
    )
    blocked = [
        item
        for item in report.review_required_items
        if item["target_field_id"] == "effective_date"
        and item["source_field_name"] == "发布日期"
    ]
    assert blocked
    assert blocked[0]["badcase_filter"]["blocked"] is True
