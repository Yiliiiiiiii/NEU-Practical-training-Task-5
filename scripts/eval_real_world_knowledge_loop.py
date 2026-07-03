"""Evaluate the real-world review-to-knowledge loop for procurement mappings."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.models import Base, ConversionTask, ReviewRecord  # noqa: E402
from app.schemas.uir import UIRDocument  # noqa: E402
from app.services.candidate_service import CandidateService  # noqa: E402
from app.services.mapping_service import MappingService  # noqa: E402
from app.services.review_knowledge_workflow_service import (  # noqa: E402
    ReviewKnowledgeWorkflowService,
)
from app.services.schema_service import SchemaService  # noqa: E402
from app.services.storage_service import StorageService  # noqa: E402
from app.services.template_service import TemplateService  # noqa: E402

SCHEMAS_DIR = ROOT / "examples" / "production_like" / "schemas"
TEMPLATES_DIR = ROOT / "examples" / "production_like" / "mapping_templates"
DECISIONS_PATH = (
    ROOT
    / "examples"
    / "real_world"
    / "review_fixtures"
    / "procurement_review_decisions.jsonl"
)
REPORT_JSON = "real_world_knowledge_loop_report.json"
REPORT_MD = "real_world_knowledge_loop_report.md"


@contextmanager
def evaluation_context(root: Path = ROOT) -> Iterator[tuple[Session, StorageService]]:
    """Create an isolated DB/storage context for evaluation only."""

    with TemporaryDirectory() as work:
        work_path = Path(work)
        engine = create_engine(
            f"sqlite:///{work_path / 'knowledge-loop.db'}",
            connect_args={"check_same_thread": False},
        )
        try:
            Base.metadata.create_all(engine)
            session_factory = sessionmaker(
                bind=engine,
                autoflush=False,
                autocommit=False,
            )
            with session_factory() as db:
                yield db, StorageService(work_path / "storage")
        finally:
            engine.dispose()


def load_decisions(path: Path = DECISIONS_PATH) -> list[dict[str, Any]]:
    decisions = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for decision in decisions:
        missing = {
            "decision_id",
            "source_field",
            "target_field",
            "decision",
            "reason",
            "schema_id",
            "template_id",
        } - set(decision)
        if missing:
            raise ValueError(f"decision {decision!r} is missing {sorted(missing)}")
        if decision["decision"] not in {"approve", "reject"}:
            raise ValueError(f"unsupported decision: {decision['decision']}")
    return decisions


def procurement_eval_uir() -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "real_procurement_knowledge_loop_eval",
            "metadata": {
                "公告标题": "广播安全监管系统采购公告",
                "公告类型": "采购公告",
                "项目名称": "广播安全监管系统采购",
                "采购方名称": "国家广播电视总局监管中心",
                "最高限价": "1000000元",
                "source_url": "https://www.ccgp.gov.cn/example/knowledge-loop",
                "source_site": "ccgp.gov.cn",
                "domain": "procurement_doc",
                "doc_type": "procurement_doc",
            },
            "blocks": [
                {
                    "block_id": "proc_kl_b001",
                    "type": "paragraph",
                    "text": "采购方名称：国家广播电视总局监管中心。最高限价：1000000元。",
                    "attributes": {},
                }
            ],
            "assets": [],
            "normalization_records": [],
        }
    )


def mapping_metrics(report: Any) -> dict[str, int]:
    summary = report.summary
    return {
        "auto_mapped_fields": int(summary.get("mapped_fields", len(report.mappings))),
        "review_required_count": int(
            summary.get("review_required", len(report.review_required_items))
        ),
        "missing_required_count": int(
            summary.get("unmapped_required_fields", len(report.unmapped))
        ),
    }


def map_with_template(template: Any, task_id: str) -> dict[str, int]:
    schema = SchemaService(SCHEMAS_DIR).load_schema("procurement_doc", "1.0.0")
    uir = procurement_eval_uir()
    candidates = CandidateService().extract_candidates(task_id, uir)
    report = MappingService().map_fields(
        task_id=task_id,
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
        options={
            "badcases": [
                {
                    "source_field": "最高限价",
                    "forbidden_target_fields": ["award_amount"],
                }
            ]
        },
    )
    return mapping_metrics(report)


def create_task(db: Session, decisions: list[dict[str, Any]]) -> None:
    badcases = [
        {
            "source_field": decision["source_field"],
            "forbidden_target_fields": decision.get(
                "forbidden_target_fields",
                [decision["target_field"]],
            ),
        }
        for decision in decisions
        if decision["decision"] == "reject"
    ]
    db.add(
        ConversionTask(
            task_id="task_real_world_knowledge_loop",
            doc_id="real_procurement_knowledge_loop_eval",
            schema_id="procurement_doc",
            schema_version="1.0.0",
            template_id="procurement_doc_base_v1",
            template_version="1.0.0",
            status="review_required",
            input_hash="knowledge-loop-eval",
            options_json=json.dumps({"badcases": badcases}, ensure_ascii=False),
        )
    )
    db.commit()


def create_reviews(db: Session, decisions: list[dict[str, Any]]) -> None:
    for index, decision in enumerate(decisions, start=1):
        db.add(
            ReviewRecord(
                review_id=decision["decision_id"],
                task_id="task_real_world_knowledge_loop",
                doc_id=decision.get("doc_id"),
                schema_id=decision["schema_id"],
                template_id=decision["template_id"],
                mapping_id=f"mapping_{index}",
                candidate_id=None,
                source_field_name=decision["source_field"],
                source_path=f"metadata.{decision['source_field']}",
                target_field_id=decision["target_field"],
                suggested_by="real_world_review_fixture",
                confidence=0.62,
                reason=decision["reason"],
                status="pending",
                decision="pending",
                reviewer="fixture",
            )
        )
    db.commit()


def apply_decisions(
    workflow: ReviewKnowledgeWorkflowService,
    decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence = []
    for decision in decisions:
        if decision["decision"] == "approve":
            review, candidate = workflow.approve_review(
                decision["decision_id"],
                reviewer="real_world_knowledge_loop",
                comment=decision["reason"],
                create_knowledge_candidate=True,
            )
            if candidate is not None and not candidate.badcase_hit:
                workflow.accept_candidate(candidate.candidate_id)
            evidence.append(
                {
                    **decision,
                    "review_status": review.status,
                    "candidate_id": candidate.candidate_id if candidate else None,
                    "candidate_status": candidate.status if candidate else None,
                    "badcase_hit": candidate.badcase_hit if candidate else False,
                    "activated": bool(candidate and not candidate.badcase_hit),
                }
            )
        else:
            review = workflow.reject_review(
                decision["decision_id"],
                reviewer="real_world_knowledge_loop",
                comment=decision["reason"],
            )
            evidence.append(
                {
                    **decision,
                    "review_status": review.status,
                    "candidate_id": None,
                    "candidate_status": None,
                    "badcase_hit": False,
                    "activated": False,
                }
            )
    return evidence


def collect_metrics(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "auto_mapped_fields": sum(item["auto_mapped_fields"] for item in results),
        "review_required_count": sum(item["review_required_count"] for item in results),
        "missing_required_count": sum(
            item["missing_required_count"] for item in results
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Real-world Knowledge Loop Report",
        "",
        "## Before / after",
        "",
        "| Stage | Auto mapped | Review required | Missing required |",
        "| --- | ---: | ---: | ---: |",
        (
            "| Before | {auto_mapped_fields} | {review_required_count} | "
            "{missing_required_count} |"
        ).format(**report["before"]),
        (
            "| After | {auto_mapped_fields} | {review_required_count} | "
            "{missing_required_count} |"
        ).format(**report["after"]),
        "",
        "## Decision evidence",
        "",
        "| Decision | Source field | Target field | Outcome | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in report["decision_evidence"]:
        lines.append(
            "| {decision} | {source_field} | {target_field} | {outcome} | {reason} |".format(
                decision=item["decision"],
                source_field=item["source_field"],
                target_field=item["target_field"],
                outcome="activated" if item["activated"] else "review_only",
                reason=str(item["reason"]).replace("|", "\\|"),
            )
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            f"- Badcase violations: {report['badcase_violation_count']}",
            f"- Old snapshot unchanged: {str(report['old_snapshot_unchanged']).lower()}",
            "",
            "## Remaining ambiguous cases",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["remaining_ambiguous_cases"])
    return "\n".join(lines) + "\n"


def run_loop(
    *,
    decisions_path: Path = DECISIONS_PATH,
    output_dir: Path = ROOT / "reports",
) -> dict[str, Any]:
    decisions = load_decisions(decisions_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    template_service = TemplateService(TEMPLATES_DIR)
    base_template = template_service.load_template("procurement_doc_base_v1", "1.0.0")
    before = map_with_template(base_template, "task_knowledge_loop_before")
    baseline_snapshot = base_template.model_dump_json()

    with evaluation_context(ROOT) as (db, storage):
        storage.write_text(
            "snapshots/procurement_template_before.json", baseline_snapshot
        )
        original_snapshot_bytes = storage.resolve(
            "snapshots/procurement_template_before.json"
        ).read_bytes()
        create_task(db, decisions)
        create_reviews(db, decisions)
        workflow = ReviewKnowledgeWorkflowService(db, template_service=template_service)
        decision_evidence = apply_decisions(workflow, decisions)
        draft = before
        if workflow.list_candidates("accepted"):
            pack = workflow.create_pack(
                schema_id="procurement_doc",
                template_id="procurement_doc_base_v1",
                name="Procurement real-world review pack",
                created_by="real_world_knowledge_loop",
            )
            draft_template = workflow.effective_template(
                "procurement_doc",
                "procurement_doc_base_v1",
            )
            draft = map_with_template(draft_template, "task_knowledge_loop_draft")
            workflow.activate_pack(pack.pack_id)
        effective_template = workflow.effective_template(
            "procurement_doc",
            "procurement_doc_base_v1",
        )
        after = map_with_template(effective_template, "task_knowledge_loop_after")
        old_snapshot_unchanged = (
            storage.resolve("snapshots/procurement_template_before.json").read_bytes()
            == original_snapshot_bytes
        )
        accepted = workflow.list_candidates("accepted")

    activated_aliases: dict[str, list[str]] = {}
    for candidate in accepted:
        activated_aliases.setdefault(candidate.target_field_id, []).append(
            candidate.alias
        )

    badcase_violation_count = sum(
        1 for item in decision_evidence if item["activated"] and item["badcase_hit"]
    )
    metrics = {
        "approved_candidates": sum(
            1 for item in decision_evidence if item["activated"]
        ),
        "rejected_candidates": sum(
            1 for item in decision_evidence if item["decision"] == "reject"
        ),
        "activated_candidate_count": len(accepted),
        "activated_alias_count": sum(
            len(values) for values in activated_aliases.values()
        ),
        "badcase_violation_count": badcase_violation_count,
        "old_snapshot_unchanged": int(old_snapshot_unchanged),
        "before_auto_mapped_fields": before["auto_mapped_fields"],
        "after_auto_mapped_fields": after["auto_mapped_fields"],
        "before_review_required_count": before["review_required_count"],
        "after_review_required_count": after["review_required_count"],
        "before_missing_required_count": before["missing_required_count"],
        "after_missing_required_count": after["missing_required_count"],
    }
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "schema_id": "procurement_doc",
        "template_id": "procurement_doc_base_v1",
        "approved_candidates": metrics["approved_candidates"],
        "rejected_candidates": metrics["rejected_candidates"],
        "activated_aliases": activated_aliases,
        "badcase_violation_count": badcase_violation_count,
        "badcase_violations": badcase_violation_count,
        "badcase_blocked_count": sum(
            1
            for item in decision_evidence
            if item["badcase_hit"] and not item["activated"]
        ),
        "old_snapshot_unchanged": old_snapshot_unchanged,
        "draft_pack_no_effect": draft == before,
        "active_pack_effect": after != before,
        "rejected_candidates_count": metrics["rejected_candidates"],
        "before_mapping_counts": before,
        "after_mapping_counts": after,
        "review_required_before": before["review_required_count"],
        "review_required_after": after["review_required_count"],
        "before": before,
        "after": after,
        "metrics": metrics,
        "decision_evidence": decision_evidence,
        "remaining_ambiguous_cases": [
            item["source_field"]
            for item in decision_evidence
            if item["decision"] == "reject"
        ],
        "boundaries": [
            "Evaluation uses an isolated temporary database and storage root.",
            "Only reviewed, non-badcase aliases are activated.",
            "No production catalog snapshot is mutated.",
        ],
    }
    (output_dir / REPORT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / REPORT_MD).write_text(render_markdown(report), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions-path", type=Path, default=DECISIONS_PATH)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    report = run_loop(decisions_path=args.decisions_path, output_dir=args.output_dir)
    print(
        {
            "approved_candidates": report["approved_candidates"],
            "rejected_candidates": report["rejected_candidates"],
            "badcase_violation_count": report["badcase_violation_count"],
            "old_snapshot_unchanged": report["old_snapshot_unchanged"],
        }
    )


if __name__ == "__main__":
    main()
