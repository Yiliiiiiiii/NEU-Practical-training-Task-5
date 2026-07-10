"""Evaluate Topic 5 upstream entity passthrough with declared chunk expectations."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for import_path in (ROOT, BACKEND):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.schemas.canonical import CanonicalModel  # noqa: E402
from app.schemas.reports import MappingReport  # noqa: E402
from app.schemas.target_schema import TargetSchema  # noqa: E402
from app.services.chunk_organizer_service import ChunkOrganizerService  # noqa: E402
from scripts.topic5_eval_common import (  # noqa: E402
    build_case_report,
    load_case_fixture,
    write_json_report,
)


DEFAULT_FIXTURE = ROOT / "eval" / "topic5_entity_passthrough" / "v2" / "cases.json"
DEFAULT_OUTPUT = ROOT / "reports" / "topic5_batch_2" / "entity_passthrough.json"
DATASET_ID = "topic5_entity_passthrough"


def load_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    return load_case_fixture(path, dataset_id=DATASET_ID)


def _identity(entity: dict[str, Any]) -> str:
    normalized_id = entity.get("normalized_id")
    if normalized_id:
        return str(normalized_id)
    return f"mention:{entity.get('mention')}:{entity.get('link_status')}"


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    canonical = CanonicalModel.model_validate(
        {
            "canonical_version": "1.0",
            "task_id": f"entity-{case['case_id']}",
            "doc_id": case["case_id"],
            "schema_id": "entity_eval",
            "doc_meta": {"entities": case["entities"]},
            "blocks": case["blocks"],
        }
    )
    schema = TargetSchema.model_validate(
        {
            "schema_id": "entity_eval",
            "name": "Entity Evaluation",
            "version": "1.0.0",
            "fields": [
                {
                    "field_id": "title",
                    "name": "title",
                    "display_name": "Title",
                    "type": "string",
                    "required": False,
                }
            ],
        }
    )
    mapping = MappingReport(
        task_id=f"entity-{case['case_id']}",
        schema_id="entity_eval",
        summary={},
        mappings=[],
        unmapped=[],
        review_required_items=[],
    )
    chunks, _report = ChunkOrganizerService().organize_chunks(
        chunks=case["chunks"],
        canonical_model=canonical,
        schema=schema,
        mapping_report=mapping,
        validation_report=None,
        task_id=f"entity-{case['case_id']}",
        doc_id=case["case_id"],
        schema_id="entity_eval",
        template_id="entity-eval-v2",
        options=None,
    )
    actual = [
        [_identity(tag) for tag in chunk.get("entity_tags", [])] for chunk in chunks
    ]
    expected = case["expected_entity_keys_by_chunk"]
    matched_count = sum(
        sum((Counter(expected_keys) & Counter(actual_keys)).values())
        for expected_keys, actual_keys in zip(expected, actual, strict=True)
    )
    expected_count = sum(len(keys) for keys in expected)
    upstream_ids = {
        str(entity["normalized_id"])
        for entity in case["entities"]
        if entity.get("normalized_id")
    }
    actual_ids = {
        str(tag["normalized_id"])
        for chunk in chunks
        for tag in chunk.get("entity_tags", [])
        if tag.get("normalized_id")
    }
    invented_ids = sorted(actual_ids - upstream_ids)
    return {
        "case_id": case["case_id"],
        "passed": actual == expected and not invented_ids,
        "expected_entity_keys_by_chunk": expected,
        "actual_entity_keys_by_chunk": actual,
        "matched_count": matched_count,
        "expected_count": expected_count,
        "invented_entity_ids": invented_ids,
    }


def build_report(fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    fixture = load_fixture(fixture_path)
    cases = [evaluate_case(case) for case in fixture["cases"]]
    expected_count = sum(case["expected_count"] for case in cases)
    matched_count = sum(case["matched_count"] for case in cases)
    invented_count = sum(len(case["invented_entity_ids"]) for case in cases)
    return build_case_report(
        fixture_path=fixture_path,
        fixture=fixture,
        cases=cases,
        metrics={
            "entity_passthrough_coverage": (
                1.0 if expected_count == 0 else matched_count / expected_count
            ),
            "invented_entity_id_count": invented_count,
        },
        reproduction_command="python scripts/eval_topic5_entity_passthrough.py",
        claim_boundary=(
            "Measures preservation of declared upstream entity identities in relevant "
            "chunks; it does not evaluate entity recognition or linking accuracy."
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    write_json_report(build_report(args.fixture), args.output)


if __name__ == "__main__":
    main()
