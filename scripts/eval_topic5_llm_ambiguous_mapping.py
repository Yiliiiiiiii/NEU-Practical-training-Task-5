"""Evaluate review-only LLM fallback on deterministic ambiguous mapping cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.schemas.mapping import FieldCandidate  # noqa: E402
from app.schemas.mapping_template import MappingTemplate  # noqa: E402
from app.schemas.target_schema import TargetField, TargetSchema  # noqa: E402
from app.schemas.uir import UIRDocument  # noqa: E402
from app.services.llm_fallback_service import LLMFallbackService  # noqa: E402
from app.services.mapping_service import MappingService  # noqa: E402

CASES = (
    ("action_items", "unlabeled_followup_fragment", "Arrange the next coordination step."),
    ("deadline", "temporal_reference_fragment", "After the review window closes."),
    ("organizer", "unnamed_responsible_party", "The responsible party will coordinate."),
)
PRODUCTION_RULE_PATHS = (
    ROOT / "backend" / "app" / "services" / "mapping_service.py",
    ROOT / "examples" / "production_like" / "schemas",
    ROOT / "examples" / "production_like" / "mapping_templates",
)


def _file_digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    files = sorted(
        path
        for root in paths
        for path in ([root] if root.is_file() else root.rglob("*"))
        if path.is_file()
    )
    for path in files:
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _evaluate_case(
    target_id: str, source_name: str, value: str
) -> dict[str, Any]:
    task_id = f"topic5_llm_ambiguous_{target_id}"
    field = TargetField(
        field_id=target_id,
        name=target_id,
        display_name=target_id.replace("_", " ").title(),
        type="string",
    )
    schema = TargetSchema(
        schema_id="topic5_llm_ambiguous",
        name="Topic 5 ambiguous mapping evaluation",
        version="1.0.0",
        fields=[field],
    )
    template = MappingTemplate(
        template_id="topic5_llm_ambiguous_v1",
        schema_id=schema.schema_id,
        name="Topic 5 ambiguous mapping evaluation",
        version="1.0.0",
    )
    uir = UIRDocument(uir_version="1.0", doc_id=f"doc_{target_id}")
    candidate = FieldCandidate(
        candidate_id=f"candidate_{target_id}",
        task_id=task_id,
        doc_id=uir.doc_id,
        source_path=f"$.ambiguous.{source_name}",
        source_name=source_name,
        value_sample=value,
        inferred_type="string",
        confidence=0.25,
        evidence=["Unlabeled semantic fragment with no deterministic target hint."],
    )
    settings = Settings(llm_fallback_enabled=True, llm_mode="mock", _env_file=None)
    report = MappingService(
        llm_fallback_service=LLMFallbackService(settings)
    ).map_fields(
        task_id=task_id,
        uir=uir,
        schema=schema,
        template=template,
        candidates=[candidate],
        options={"enable_llm_fallback": True},
    )
    llm_items = [
        item
        for item in report.review_required_items
        if item.get("method") == "llm_fallback"
    ]
    item = llm_items[0] if llm_items else {}
    return {
        "case_id": target_id,
        "ambiguity": "No exact, alias, regex, type, evidence-hint, or fuzzy mapping applies.",
        "llm_fallback_exercised": bool(llm_items),
        "method": item.get("method"),
        "status": item.get("status"),
        "need_review": item.get("need_review"),
        "confidence": item.get("confidence"),
        "review_required_reason": item.get("review_required_reason"),
        "evidence": item.get("evidence", []),
        "evidence_text": item.get("evidence_text", []),
        "auto_accept_allowed": False,
    }


def evaluate() -> dict[str, Any]:
    before = _file_digest(PRODUCTION_RULE_PATHS)
    cases = [_evaluate_case(*case) for case in CASES]
    after = _file_digest(PRODUCTION_RULE_PATHS)
    metrics = {
        "ambiguous_case_count": len(cases),
        "llm_fallback_exercised_count": sum(
            bool(case["llm_fallback_exercised"]) for case in cases
        ),
        "review_required_count": sum(
            case["status"] == "review_required" and case["need_review"] is True
            for case in cases
        ),
        "auto_accepted_count": sum(case["status"] == "accepted" for case in cases),
        "confidence_bound_violations": sum(
            not isinstance(case["confidence"], int | float)
            or not 0.0 <= float(case["confidence"]) <= 0.65
            for case in cases
        ),
        "missing_reason_count": sum(
            not str(case["review_required_reason"] or "").strip() for case in cases
        ),
        "missing_evidence_count": sum(
            not case["evidence"] or not case["evidence_text"] for case in cases
        ),
        "production_rule_catalog_unchanged": before == after,
        "network_used": False,
    }
    passed = (
        metrics["ambiguous_case_count"] >= 1
        and metrics["llm_fallback_exercised_count"] == metrics["ambiguous_case_count"]
        and metrics["review_required_count"] == metrics["ambiguous_case_count"]
        and metrics["auto_accepted_count"] == 0
        and metrics["confidence_bound_violations"] == 0
        and metrics["missing_reason_count"] == 0
        and metrics["missing_evidence_count"] == 0
        and metrics["production_rule_catalog_unchanged"] is True
    )
    return {
        "status": "passed" if passed else "failed",
        "passed": passed,
        "adapter_mode": "deterministic_stub",
        "metrics": metrics,
        "cases": cases,
        "claim_boundary": (
            "Deterministic offline difficult-case evaluation only; suggestions are "
            "review-required and do not establish live-provider quality."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
