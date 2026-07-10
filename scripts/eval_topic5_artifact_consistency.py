"""Evaluate Topic 5 artifact consistency and declared tampering cases."""

from __future__ import annotations

import argparse
import copy
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for import_path in (ROOT, BACKEND):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.schemas.canonical import CanonicalModel  # noqa: E402
from app.schemas.document_summary import DocumentSummary  # noqa: E402
from app.services.artifact_consistency_service import ArtifactConsistencyService  # noqa: E402
from app.services.render_service import RenderService  # noqa: E402
from scripts.topic5_eval_common import (  # noqa: E402
    build_case_report,
    load_case_fixture,
    write_json_report,
)


DEFAULT_FIXTURE = ROOT / "eval" / "topic5_artifact_consistency" / "v2" / "cases.json"
DEFAULT_OUTPUT = ROOT / "reports" / "topic5_batch_2" / "artifact_consistency.json"
DATASET_ID = "topic5_artifact_consistency"


def load_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    fixture = load_case_fixture(path, dataset_id=DATASET_ID)
    if not isinstance(fixture.get("base"), dict):
        raise ValueError("artifact-consistency fixture requires a base artifact")
    return fixture


def evaluate_case(case: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    summary = DocumentSummary.model_validate(base["document_summary"])
    canonical_payload = copy.deepcopy(base["canonical"])
    canonical_payload.setdefault("doc_meta", {})["document_summary"] = summary.model_dump(
        mode="json"
    )
    canonical = CanonicalModel.model_validate(canonical_payload)
    rendered = RenderService().render(canonical)
    structured = copy.deepcopy(rendered.structured_json)
    markdown = rendered.markdown
    chunks = copy.deepcopy(base["chunks"])

    mutation = case["mutation"]
    if mutation == "structured_field_change":
        structured["data"][case["field_id"]] = case["replacement"]
    elif mutation == "markdown_block_omission":
        block_id = re.escape(case["block_id"])
        markdown = re.sub(
            rf'<!-- topic5:block:start id="{block_id}".*?'
            rf'<!-- topic5:block:end id="{block_id}" -->\n?',
            "",
            markdown,
            flags=re.DOTALL,
        )
    elif mutation == "chunk_unknown_source":
        chunks[case["chunk_index"]]["source_block_ids"] = ["unknown"]
    elif mutation != "none":
        raise ValueError(f"unsupported artifact mutation: {mutation}")

    report = ArtifactConsistencyService().verify(
        canonical=canonical,
        structured_json=structured,
        markdown=markdown,
        chunks=chunks,
        document_summary=summary,
    )
    error_codes = [issue.error_code for issue in report.errors]
    expected_code = case.get("expected_error_code")
    detected = report.passed is False and (
        expected_code is None or expected_code in error_codes
    )
    passed = report.passed is case["expected_report_passed"] and (
        expected_code is None or expected_code in error_codes
    )
    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "passed": passed,
        "expected_report_passed": case["expected_report_passed"],
        "actual_report_passed": report.passed,
        "error_codes": error_codes,
        "tampering_detected": detected if case["category"] == "tampering" else None,
        "block_coverage": report.block_coverage,
        "chunk_source_coverage": report.chunk_source_coverage,
    }


def build_report(fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    fixture = load_fixture(fixture_path)
    cases = [evaluate_case(case, fixture["base"]) for case in fixture["cases"]]
    baselines = [case for case in cases if case["category"] == "baseline"]
    tampering = [case for case in cases if case["category"] == "tampering"]
    return build_case_report(
        fixture_path=fixture_path,
        fixture=fixture,
        cases=cases,
        metrics={
            "artifact_consistency_pass_rate": (
                sum(case["actual_report_passed"] for case in baselines) / len(baselines)
            ),
            "markdown_block_coverage": (
                sum(case["block_coverage"] for case in baselines) / len(baselines)
            ),
            "chunk_source_coverage": (
                sum(case["chunk_source_coverage"] for case in baselines) / len(baselines)
            ),
            "tampering_detection_rate": (
                sum(case["tampering_detected"] for case in tampering) / len(tampering)
            ),
        },
        reproduction_command="python scripts/eval_topic5_artifact_consistency.py",
        claim_boundary=(
            "Measures declared JSON/Markdown/chunk consistency and deterministic tampering "
            "detection; it does not establish cryptographic package authenticity."
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
