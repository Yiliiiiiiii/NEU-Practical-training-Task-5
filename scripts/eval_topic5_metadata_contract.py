"""Evaluate Topic 5 metadata-template behavior with declared case expectations."""

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

from app.schemas.metadata_template import MetadataTemplateConfig  # noqa: E402
from app.schemas.uir import UIRDocument  # noqa: E402
from app.services.metadata_template_service import MetadataTemplateService  # noqa: E402
from scripts.topic5_eval_common import (  # noqa: E402
    build_case_report,
    load_case_fixture,
    write_json_report,
)


DEFAULT_FIXTURE = ROOT / "eval" / "topic5_metadata_contract" / "v2" / "cases.json"
DEFAULT_OUTPUT = ROOT / "reports" / "topic5_batch_2" / "metadata_contract.json"
DATASET_ID = "topic5_metadata_contract"


def load_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    return load_case_fixture(path, dataset_id=DATASET_ID)


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    template = MetadataTemplateConfig.model_validate(
        {
            "template_id": f"{case['case_id']}-template",
            "schema_id": "topic5_metadata_eval",
            "version": "2.0.0",
            "metadata_fields": case["metadata_fields"],
        }
    )
    result = MetadataTemplateService().render(
        uir=UIRDocument.model_validate(
            {
                "uir_version": "1.0",
                "doc_id": case["case_id"],
                "metadata": case.get("metadata", {}),
                "blocks": [],
            }
        ),
        transformed_fields=case.get("transformed_fields", {}),
        template=template,
        system_context={"doc_id": case["case_id"]},
    )
    issues = [
        {
            "stage": issue.stage,
            "path": issue.path,
            "error_code": issue.error_code,
        }
        for issue in result.report.issues
    ]
    expected_issue = case.get("expected_issue")
    issue_localized = expected_issue is None or expected_issue in issues
    passed = (
        result.passed is case["expected_passed"]
        and result.document_metadata == case["expected_document_metadata"]
        and issue_localized
    )
    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "passed": passed,
        "expected_passed": case["expected_passed"],
        "actual_passed": result.passed,
        "expected_document_metadata": case["expected_document_metadata"],
        "actual_document_metadata": result.document_metadata,
        "expected_issue": expected_issue,
        "actual_issues": issues,
        "issue_localized": issue_localized,
    }


def build_report(fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    fixture = load_fixture(fixture_path)
    cases = [evaluate_case(case) for case in fixture["cases"]]
    effectiveness = [case for case in cases if case["category"] == "effectiveness"]
    localization = [case for case in cases if case["category"] == "localization"]
    effectiveness_rate = sum(case["passed"] for case in effectiveness) / len(effectiveness)
    localization_rate = sum(case["issue_localized"] for case in localization) / len(
        localization
    )
    return build_case_report(
        fixture_path=fixture_path,
        fixture=fixture,
        cases=cases,
        metrics={
            "metadata_template_effective": effectiveness_rate == 1.0,
            "metadata_template_effectiveness_rate": effectiveness_rate,
            "metadata_required_localization_rate": localization_rate,
        },
        reproduction_command="python scripts/eval_topic5_metadata_contract.py",
        claim_boundary=(
            "Measures declared metadata-template rendering and exact issue localization; "
            "it does not measure upstream extraction quality."
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
