"""Evaluate Topic 5 document-summary faithfulness from declared source cases."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for import_path in (ROOT, BACKEND):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.schemas.canonical import CanonicalModel  # noqa: E402
from app.schemas.content_organization import SummaryConfig  # noqa: E402
from app.services.document_summary_service import DocumentSummaryService  # noqa: E402
from scripts.topic5_eval_common import (  # noqa: E402
    build_case_report,
    load_case_fixture,
    write_json_report,
)


DEFAULT_FIXTURE = ROOT / "eval" / "topic5_summary_faithfulness" / "v2" / "cases.json"
DEFAULT_OUTPUT = ROOT / "reports" / "topic5_batch_2" / "summary_faithfulness.json"
DATASET_ID = "topic5_summary_faithfulness"


def load_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    return load_case_fixture(path, dataset_id=DATASET_ID)


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    canonical = CanonicalModel.model_validate(
        {
            "canonical_version": "1.0",
            "task_id": f"summary-{case['case_id']}",
            "doc_id": case["case_id"],
            "schema_id": "summary_eval",
            "blocks": case["blocks"],
        }
    )
    summary = DocumentSummaryService().build(
        canonical=canonical,
        chunks=case.get("chunks", []),
        config=SummaryConfig.model_validate(case.get("config", {})),
    )
    if summary is None:
        return {
            "case_id": case["case_id"],
            "passed": False,
            "faithful": False,
            "source_coverage": 0.0,
            "new_fact_violations": 1,
            "actual_summary": None,
        }

    blocks = {block.block_id: block.text for block in canonical.blocks}
    new_fact_violations = sum(
        trace.source_block_id not in blocks
        or trace.source_text_span not in blocks.get(trace.source_block_id, "")
        or trace.summary_sentence != trace.source_text_span
        for trace in summary.sentence_traces
    )
    faithful = summary.faithfulness_passed and new_fact_violations == 0
    expected_blocks = set(case.get("expected_source_block_ids", []))
    expected_chunks = set(case.get("expected_source_chunk_ids", []))
    expected_sources = len(expected_blocks) + len(expected_chunks)
    covered_sources = len(expected_blocks.intersection(summary.source_block_ids)) + len(
        expected_chunks.intersection(summary.source_chunk_ids)
    )
    source_coverage = 1.0 if expected_sources == 0 else covered_sources / expected_sources
    passed = (
        summary.text == case["expected_text"]
        and summary.source_block_ids == case.get("expected_source_block_ids", [])
        and summary.source_chunk_ids == case.get("expected_source_chunk_ids", [])
        and faithful
        and source_coverage == 1.0
    )
    return {
        "case_id": case["case_id"],
        "passed": passed,
        "faithful": faithful,
        "source_coverage": source_coverage,
        "new_fact_violations": new_fact_violations,
        "expected_text": case["expected_text"],
        "actual_summary": summary.model_dump(mode="json"),
    }


def build_report(fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    fixture = load_fixture(fixture_path)
    cases = [evaluate_case(case) for case in fixture["cases"]]
    total = len(cases)
    return build_case_report(
        fixture_path=fixture_path,
        fixture=fixture,
        cases=cases,
        metrics={
            "document_summary_faithfulness": (
                sum(case["faithful"] for case in cases) / total
            ),
            "document_summary_source_coverage": (
                sum(case["source_coverage"] for case in cases) / total
            ),
            "document_summary_new_fact_violations": sum(
                case["new_fact_violations"] for case in cases
            ),
        },
        reproduction_command="python scripts/eval_topic5_summary_faithfulness.py",
        claim_boundary=(
            "Measures extractive summary traces, declared source coverage, and facts absent "
            "from those traces; it does not grade abstractiveness or writing quality."
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
