"""Evaluate semantic equivalence of inline and registered Topic 5 contexts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.schemas.content_organization import ContentOrganizationOptions  # noqa: E402
from app.schemas.mapping_template import MappingTemplate  # noqa: E402
from app.schemas.target_schema import TargetSchema  # noqa: E402
from app.schemas.topic5_convert import Topic5ConvertRequest  # noqa: E402
from app.schemas.topic5_execution import Topic5ExecutionOptions  # noqa: E402
from app.schemas.uir import UIRDocument  # noqa: E402
from app.services.conversion_fingerprint_service import (  # noqa: E402
    ConversionFingerprintService,
)
from app.services.topic5_conversion_engine import (  # noqa: E402
    ConversionEngineContext,
    Topic5ConversionEngine,
)

DEFAULT_OUTPUT = ROOT / "eval" / "topic5_runtime_equivalence" / "v1" / "report.json"
CASE_IDS = (
    "announcement_doc",
    "event_notice_doc",
    "general_doc",
    "meeting_doc",
    "policy_doc",
)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _case(name: str) -> tuple[Any, ...]:
    if name in {"announcement_doc", "event_notice_doc"}:
        filename = (
            "announcement_convert_request.json"
            if name == "announcement_doc"
            else "event_notice_convert_request.json"
        )
        request = Topic5ConvertRequest.model_validate(
            _json(ROOT / "examples" / "topic5_inline" / filename)
        )
        return (
            request.uir,
            request.target_schema,
            request.effective_mapping_template,
            request.content_organization,
            request.metadata_template,
        )
    family = name.removesuffix("_doc")
    uir_path = next(
        iter(
            sorted(
                (ROOT / "examples" / "production_like" / "uir" / family).glob(
                    "*.json"
                )
            )
        )
    )
    return (
        UIRDocument.model_validate(_json(uir_path)),
        TargetSchema.model_validate(
            _json(
                ROOT
                / "examples"
                / "production_like"
                / "schemas"
                / f"{name}_v1.json"
            )
        ),
        MappingTemplate.model_validate(
            _json(
                ROOT
                / "examples"
                / "production_like"
                / "mapping_templates"
                / f"{name}_base_v1.json"
            )
        ),
        ContentOrganizationOptions(),
        None,
    )


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def run_evaluation(*, commit_sha: str | None = None) -> dict[str, Any]:
    engine = Topic5ConversionEngine()
    options = Topic5ExecutionOptions(
        mapping_mode="legacy",
        enable_llm_fallback=False,
        enable_legacy_candidate_heuristics=False,
    )
    cases: list[dict[str, Any]] = []
    fixture_contract: list[dict[str, Any]] = []
    for case_id in CASE_IDS:
        uir, schema, mapping, content_org, metadata = _case(case_id)
        fixture_contract.append(
            {
                "case_id": case_id,
                "input": ConversionFingerprintService.conversion_fingerprints(
                    uir=uir,
                    target_schema=schema,
                    metadata_template=metadata,
                    mapping_rules=mapping,
                    content_organization=content_org,
                    execution_options=options,
                ),
            }
        )
        results = []
        for task_id, mode in (
            (f"inline-{case_id}", "inline_topic5_config"),
            (f"registered-{case_id}", "registered_task"),
        ):
            results.append(
                engine.convert(
                    uir=uir,
                    target_schema=schema,
                    metadata_template=metadata,
                    mapping_rules=mapping,
                    content_organization=content_org,
                    execution_options=options,
                    output_assertions=None,
                    engine_context=ConversionEngineContext(
                        task_id=task_id,
                        doc_id=uir.doc_id,
                        input_mode=mode,
                        mapping_input_name="mapping_rules",
                        settings=Settings(),
                    ),
                )
            )
        inline, registered = results
        mismatches = sorted(
            key
            for key in inline.semantic_artifact_hashes
            if inline.semantic_artifact_hashes[key]
            != registered.semantic_artifact_hashes.get(key)
        )
        if inline.conversion_fingerprints != registered.conversion_fingerprints:
            mismatches.append("conversion_fingerprint")
        cases.append(
            {
                "case_id": case_id,
                "passed": not mismatches,
                "mismatches": mismatches,
                "conversion_fingerprint": inline.conversion_fingerprints[
                    "conversion_fingerprint"
                ],
                "semantic_artifact_hashes": inline.semantic_artifact_hashes,
            }
        )
    dataset_sha = hashlib.sha256(
        ConversionFingerprintService.canonical_bytes(fixture_contract)
    ).hexdigest()
    passed_count = sum(case["passed"] for case in cases)
    return {
        "status": "passed" if passed_count == len(cases) else "failed",
        "dataset_id": "topic5_runtime_equivalence",
        "dataset_version": "1.0.0",
        "dataset_sha256": dataset_sha,
        "commit_sha": commit_sha or _git_head(),
        "engine_version": ConversionFingerprintService.ENGINE_VERSION,
        "case_count": len(cases),
        "passed_count": passed_count,
        "inline_registered_semantic_equivalence": passed_count / len(cases),
        "failed_cases": [case for case in cases if not case["passed"]],
        "cases": cases,
        "reproduction_command": "python scripts/eval_topic5_runtime_equivalence.py",
        "claim_boundary": (
            "Topic 5 semantic artifacts and reports with operational identifiers excluded"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--commit-sha")
    args = parser.parse_args()
    report = run_evaluation(commit_sha=args.commit_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
