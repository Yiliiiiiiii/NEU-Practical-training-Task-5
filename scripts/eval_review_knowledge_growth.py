"""Evaluate reviewed knowledge growth against a fixed real-world UIR fixture."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Settings
from app.db.models import Base, ConversionTask
from app.schemas.api import TaskCreateRequest
from app.schemas.uir import UIRDocument
from app.services.document_service import DocumentService
from app.services.review_knowledge_workflow_service import (
    ReviewKnowledgeWorkflowService,
)
from app.services.schema_service import SchemaService
from app.services.storage_service import StorageService
from app.services.task_execution_service import TaskExecutionService
from app.services.task_service import TaskService
from app.services.template_service import TemplateService


DECISIONS_PATH = (
    ROOT
    / "examples"
    / "real_world"
    / "review_fixtures"
    / "next_phase_review_decisions.jsonl"
)
UIR_ROOT = ROOT / "examples" / "real_world" / "uir"
SCHEMAS_ROOT = ROOT / "examples" / "production_like" / "schemas"
TEMPLATES_ROOT = ROOT / "examples" / "production_like" / "mapping_templates"
REPORT_JSON = "review_knowledge_growth_report.json"
REPORT_MD = "review_knowledge_growth_report.md"
REQUIRED_FIELDS = {
    "doc_id",
    "doc_type",
    "source_label",
    "source_value_sample",
    "target_field",
    "decision",
    "reason",
    "expected_alias_to_activate",
}
CATALOG = {
    "general_doc": ("general_doc", "general_doc_base_v1"),
    "meeting_doc": ("meeting_doc", "meeting_doc_base_v1"),
    "policy_doc": ("policy_doc", "policy_doc_base_v1"),
    "procurement_doc": ("procurement_doc", "procurement_doc_base_v1"),
}


def load_decisions(path: Path = DECISIONS_PATH) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON") from exc
        if not isinstance(item, dict):
            raise ValueError(f"line {line_number}: decision must be an object")
        missing = REQUIRED_FIELDS - item.keys()
        if missing:
            raise ValueError(f"line {line_number}: missing {sorted(missing)}")
        if item["decision"] not in {"approve", "reject"}:
            raise ValueError(
                f"line {line_number}: unsupported decision {item['decision']!r}"
            )
        expected_alias = item["expected_alias_to_activate"]
        if expected_alias is not None and not isinstance(expected_alias, str):
            raise ValueError(
                f"line {line_number}: expected_alias_to_activate must be string or null"
            )
        if expected_alias is not None and expected_alias != item["source_label"]:
            raise ValueError(
                f"line {line_number}: expected alias must match source_label"
            )
        if item["doc_type"] not in CATALOG:
            raise ValueError(
                f"line {line_number}: unsupported doc_type {item['doc_type']!r}"
            )
        decisions.append(item)
    if not decisions:
        raise ValueError("decision fixture is empty")
    if {item["decision"] for item in decisions} != {"approve", "reject"}:
        raise ValueError("decision fixture must include approve and reject controls")
    errors = validate_real_uir_references(decisions)
    if errors:
        raise ValueError("; ".join(errors))
    return decisions


def _uir_path(decision: dict[str, Any]) -> Path:
    return (
        UIR_ROOT
        / str(decision["doc_type"]).removesuffix("_doc")
        / (f"{decision['doc_id']}.json")
    )


def _source_values(uir: dict[str, Any], label: str) -> list[Any]:
    values: list[Any] = []
    metadata = uir.get("metadata", {})
    if isinstance(metadata, dict) and label in metadata:
        values.append(metadata[label])
    for block in uir.get("blocks", []):
        if not isinstance(block, dict):
            continue
        attributes = block.get("attributes", {})
        if not isinstance(attributes, dict):
            continue
        if attributes.get("field_name") == label:
            values.append(block.get("text"))
        rows = attributes.get("rows", [])
        if isinstance(rows, list):
            values.extend(
                row.get("value")
                for row in rows
                if isinstance(row, dict) and row.get("field") == label
            )
    return values


def validate_real_uir_references(
    decisions: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    for item in decisions:
        path = _uir_path(item)
        if not path.is_file():
            errors.append(f"{item['doc_id']}: real UIR not found")
            continue
        uir = json.loads(path.read_text(encoding="utf-8"))
        if uir.get("doc_id") != item["doc_id"]:
            errors.append(f"{item['doc_id']}: doc_id mismatch")
        values = _source_values(uir, str(item["source_label"]))
        sample = str(item["source_value_sample"])
        if not any(sample in str(value) for value in values):
            errors.append(
                f"{item['doc_id']}: {item['source_label']!r} does not contain {sample!r}"
            )
    return errors


@contextmanager
def isolated_state() -> (
    Iterator[tuple[Session, StorageService, SchemaService, TemplateService]]
):
    with tempfile.TemporaryDirectory(prefix="review-knowledge-growth-") as raw_root:
        root = Path(raw_root)
        schema_root = root / "catalog" / "schemas"
        template_root = root / "catalog" / "mapping_templates"
        shutil.copytree(SCHEMAS_ROOT, schema_root)
        shutil.copytree(TEMPLATES_ROOT, template_root)
        engine = create_engine(
            f"sqlite:///{root / 'evaluation.db'}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = session_factory()
        try:
            yield (
                db,
                StorageService(root / "storage"),
                SchemaService(schema_root),
                TemplateService(template_root),
            )
        finally:
            db.close()
            engine.dispose()


def _task_request(
    doc_id: str,
    schema_id: str,
    template_id: str,
    *,
    badcases: list[dict[str, Any]],
) -> TaskCreateRequest:
    return TaskCreateRequest(
        doc_id=doc_id,
        schema_id=schema_id,
        schema_version="1.0.0",
        template_id=template_id,
        template_version="1.0.0",
        options={"enable_llm_fallback": False, "badcases": badcases},
    )


def _execute_new_task(
    db: Session,
    storage: StorageService,
    schema_service: SchemaService,
    template_service: TemplateService,
    request: TaskCreateRequest,
) -> tuple[ConversionTask, dict[str, Any], dict[str, Any]]:
    task = TaskService(db, storage).create_task(request)
    executor = TaskExecutionService(
        db,
        storage,
        schema_service=schema_service,
        template_service=template_service,
        settings=Settings(
            _env_file=None,
            storage_root=str(storage.root),
            database_url="sqlite:///isolated-evaluation.db",
            llm_mode="disabled",
            llm_fallback_enabled=False,
        ),
    )
    result = executor.execute_task(task.task_id)
    mapping_report = executor.read_report(task.task_id, "mapping")
    return task, {"status": result.status}, mapping_report


def _task_artifacts(
    task: ConversionTask,
    storage: StorageService,
) -> dict[str, dict[str, Any]]:
    snapshot_path = storage.resolve(str(task.config_snapshot_path))
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    selected = {
        "metadata": Path(snapshot["report_paths"]["package_metadata"]),
        "canonical": Path(snapshot["report_paths"]["canonical"]),
        "mapping_report": Path(snapshot["report_paths"]["mapping_report"]),
        "execution_snapshot": snapshot_path,
    }
    return {
        name: {
            "bytes": path.read_bytes(),
            "structure": json.loads(path.read_text(encoding="utf-8")),
        }
        for name, path in selected.items()
    }


def _task_record_snapshot(task: ConversionTask) -> dict[str, Any]:
    return {
        column.name: (value.isoformat() if hasattr(value, "isoformat") else value)
        for column in task.__table__.columns
        if (value := getattr(task, column.name)) is not None
    }


def _stage_metrics(
    mapping_report: dict[str, Any],
    execution: dict[str, Any],
    *,
    approved_aliases: list[tuple[str, str]],
    required_field_ids: set[str],
) -> dict[str, Any]:
    accepted = [
        item
        for item in mapping_report.get("mappings", [])
        if isinstance(item, dict) and item.get("status", "accepted") == "accepted"
    ]
    mapped_pairs = {
        (
            str(item.get("source_field", {}).get("source_name")),
            str(item.get("target_field_id")),
        )
        for item in accepted
        if isinstance(item.get("source_field"), dict)
    }
    required_mapped = {
        str(item.get("target_field_id"))
        for item in accepted
        if str(item.get("target_field_id")) in required_field_ids
    }
    recall = (
        sum(pair in mapped_pairs for pair in approved_aliases) / len(approved_aliases)
        if approved_aliases
        else 1.0
    )
    return {
        "review_required_count": len(mapping_report.get("review_required_items", [])),
        "auto_mapped_fields": len(accepted),
        "mapping_recall": round(recall, 4),
        "required_coverage": round(len(required_mapped) / len(required_field_ids), 4)
        if required_field_ids
        else 1.0,
        "strict_pass_count": int(execution.get("status") != "failed"),
    }


def _matching_review(
    workflow: ReviewKnowledgeWorkflowService, task_id: str, item: dict[str, Any]
):
    matches = [
        review
        for review in workflow.list_reviews()
        if review.task_id == task_id
        and review.source_field_name == item["source_label"]
        and review.target_field_id == item["target_field"]
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{item['source_label']} -> {item['target_field']} matched {len(matches)} reviews"
        )
    return matches[0]


def run_evaluation(
    *,
    decisions_path: Path = DECISIONS_PATH,
    output_dir: Path = ROOT / "reports",
) -> dict[str, Any]:
    decisions = load_decisions(decisions_path)
    doc_ids = {str(item["doc_id"]) for item in decisions}
    doc_types = {str(item["doc_type"]) for item in decisions}
    if len(doc_ids) != 1 or len(doc_types) != 1:
        raise ValueError(
            "this deterministic evaluation requires one fixed UIR document"
        )
    doc_id = next(iter(doc_ids))
    doc_type = next(iter(doc_types))
    schema_id, template_id = CATALOG[doc_type]
    approved_aliases = [
        (str(item["source_label"]), str(item["target_field"]))
        for item in decisions
        if item["decision"] == "approve"
        and item["expected_alias_to_activate"] is not None
    ]
    badcases = [
        {
            "source_field": item["source_label"],
            "forbidden_target_fields": [item["target_field"]],
        }
        for item in decisions
        if item["decision"] == "approve" and item["expected_alias_to_activate"] is None
    ]

    with isolated_state() as (db, storage, schema_service, template_service):
        uir = UIRDocument.model_validate(
            json.loads(_uir_path(decisions[0]).read_text(encoding="utf-8"))
        )
        DocumentService(db, storage).import_uir(uir)
        request = _task_request(
            doc_id,
            schema_id,
            template_id,
            badcases=badcases,
        )
        schema = schema_service.load_schema(schema_id, "1.0.0")
        required_field_ids = {
            field.field_id
            for field in schema.fields
            if getattr(field, "required", False)
        }
        first_task, first_execution, first_mapping = _execute_new_task(
            db, storage, schema_service, template_service, request
        )
        old_artifacts = _task_artifacts(first_task, storage)
        old_task_record = _task_record_snapshot(first_task)
        workflow = ReviewKnowledgeWorkflowService(db, template_service=template_service)
        decision_evidence: list[dict[str, Any]] = []
        candidates = []
        for item in decisions:
            review = _matching_review(workflow, first_task.task_id, item)
            if item["decision"] == "approve":
                decided, candidate = workflow.approve_review(
                    review.review_id,
                    reviewer="review_knowledge_growth_eval",
                    comment=str(item["reason"]),
                    create_knowledge_candidate=True,
                )
                if candidate is None:
                    raise ValueError(
                        f"approved review {review.review_id} made no candidate"
                    )
                candidates.append(candidate)
                decision_evidence.append(
                    {
                        "decision": decided.decision,
                        "source_label": item["source_label"],
                        "target_field": item["target_field"],
                        "reason": item["reason"],
                        "candidate_status": candidate.status,
                        "badcase_hit": candidate.badcase_hit,
                    }
                )
            else:
                decided = workflow.reject_review(
                    review.review_id,
                    reviewer="review_knowledge_growth_eval",
                    comment=str(item["reason"]),
                )
                decision_evidence.append(
                    {
                        "decision": decided.decision,
                        "source_label": item["source_label"],
                        "target_field": item["target_field"],
                        "reason": item["reason"],
                        "candidate_status": None,
                        "badcase_hit": False,
                    }
                )

        for candidate in candidates:
            if candidate.status == "pending":
                workflow.accept_candidate(candidate.candidate_id)
        pack = workflow.create_pack(
            schema_id=schema_id,
            template_id=template_id,
            name="Review knowledge growth evaluation pack",
            created_by="review_knowledge_growth_eval",
        )
        _, draft_execution, draft_mapping = _execute_new_task(
            db, storage, schema_service, template_service, request
        )
        workflow.activate_pack(pack.pack_id)
        _, second_execution, second_mapping = _execute_new_task(
            db, storage, schema_service, template_service, request
        )
        after_artifacts = _task_artifacts(first_task, storage)
        task_record_unchanged = old_task_record == _task_record_snapshot(first_task)
        active_packs = workflow.active_knowledge_packs(
            schema_id=schema_id, template_id=template_id
        )

        activated_aliases: dict[str, list[str]] = {}
        for active_pack in active_packs:
            for target, aliases in active_pack.aliases.items():
                activated_aliases.setdefault(target, []).extend(aliases)
        activated_aliases = {
            target: sorted(set(aliases))
            for target, aliases in sorted(activated_aliases.items())
        }
        artifact_evidence = {
            name: {
                "bytes_unchanged": old_artifacts[name]["bytes"]
                == after_artifacts[name]["bytes"],
                "structure_unchanged": old_artifacts[name]["structure"]
                == after_artifacts[name]["structure"],
            }
            for name in old_artifacts
        }
        before = _stage_metrics(
            first_mapping,
            first_execution,
            approved_aliases=approved_aliases,
            required_field_ids=required_field_ids,
        )
        draft = _stage_metrics(
            draft_mapping,
            draft_execution,
            approved_aliases=approved_aliases,
            required_field_ids=required_field_ids,
        )
        after = _stage_metrics(
            second_mapping,
            second_execution,
            approved_aliases=approved_aliases,
            required_field_ids=required_field_ids,
        )

    rejected_controls = [
        {
            "source_label": item["source_label"],
            "target_field": item["target_field"],
            "reason": item["reason"],
            "candidate_created": False,
            "activated": item["source_label"]
            in activated_aliases.get(str(item["target_field"]), []),
        }
        for item in decisions
        if item["decision"] == "reject"
    ]
    blocked_aliases = sorted(
        str(item["source_label"])
        for item in decisions
        if item["decision"] == "approve" and item["expected_alias_to_activate"] is None
    )
    badcase_violation_count = sum(
        alias in aliases
        for alias in blocked_aliases
        for aliases in activated_aliases.values()
    )
    rejected_candidate_activated_count = sum(
        1 for item in rejected_controls if item["activated"]
    )
    old_snapshot_unchanged = all(
        evidence["bytes_unchanged"] and evidence["structure_unchanged"]
        for evidence in artifact_evidence.values()
    )
    passed = all(
        [
            old_snapshot_unchanged,
            badcase_violation_count == 0,
            rejected_candidate_activated_count == 0,
            after["review_required_count"] < before["review_required_count"],
            after["auto_mapped_fields"] > before["auto_mapped_fields"],
            after["mapping_recall"] > before["mapping_recall"],
            draft == before,
        ]
    )
    report = {
        "fixture": {
            "doc_id": doc_id,
            "doc_type": doc_type,
            "decision_count": len(decisions),
            "real_uir_path": str(_uir_path(decisions[0]).relative_to(ROOT)).replace(
                "\\", "/"
            ),
        },
        "summary": {
            "passed": passed,
            "isolated_state": True,
            "old_snapshot_unchanged": old_snapshot_unchanged,
            "badcase_violation_count": badcase_violation_count,
            "rejected_candidate_activated_count": rejected_candidate_activated_count,
        },
        "before_mapping_counts": before,
        "after_mapping_counts": after,
        "review_required_before": before["review_required_count"],
        "review_required_after": after["review_required_count"],
        "rejected_candidates_count": len(rejected_controls),
        "badcase_blocked_count": len(blocked_aliases),
        "draft_pack_no_effect": draft == before,
        "active_pack_effect": after != before,
        "old_snapshot_unchanged": old_snapshot_unchanged,
        "badcase_violations": badcase_violation_count,
        "before": before,
        "after": after,
        "activated_aliases": activated_aliases,
        "rejected_controls": rejected_controls,
        "badcase_controls": {
            "blocked_aliases": blocked_aliases,
            "violation_count": badcase_violation_count,
        },
        "decision_evidence": decision_evidence,
        "draft_pack_evidence": {
            "status": "draft",
            "affected_future_task": draft != before,
            "metrics_equal_to_before": draft == before,
        },
        "old_task_invariant": {
            "metadata_unchanged": all(artifact_evidence["metadata"].values()),
            "canonical_unchanged": all(artifact_evidence["canonical"].values()),
            "mapping_report_unchanged": all(
                artifact_evidence["mapping_report"].values()
            ),
            "execution_snapshot_unchanged": all(
                artifact_evidence["execution_snapshot"].values()
            ),
            "task_record_unchanged": task_record_unchanged,
            "artifacts": artifact_evidence,
        },
        "boundaries": [
            "A temporary SQLite database, storage root, and copied catalog are used.",
            "Draft packs are measured before activation.",
            "Only accepted, non-badcase candidates enter the active pack.",
        ],
    }
    write_reports(output_dir, report)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    before = report["before"]
    after = report["after"]
    lines = [
        "# Review Knowledge Growth Report",
        "",
        f"- Passed: {report['summary']['passed']}",
        f"- Real UIR: `{report['fixture']['real_uir_path']}`",
        f"- Old snapshot unchanged: {report['summary']['old_snapshot_unchanged']}",
        f"- Badcase violations: {report['summary']['badcase_violation_count']}",
        f"- Rejected candidates activated: {report['summary']['rejected_candidate_activated_count']}",
        "",
        "## Before / After",
        "",
        "| Stage | Review required | Auto mapped | Mapping recall | Required coverage | Strict pass |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        (
            f"| Before | {before['review_required_count']} | {before['auto_mapped_fields']} "
            f"| {before['mapping_recall']:.4f} | {before['required_coverage']:.4f} "
            f"| {before['strict_pass_count']} |"
        ),
        (
            f"| After | {after['review_required_count']} | {after['auto_mapped_fields']} "
            f"| {after['mapping_recall']:.4f} | {after['required_coverage']:.4f} "
            f"| {after['strict_pass_count']} |"
        ),
        "",
        "## Activated aliases",
        "",
    ]
    for target, aliases in report["activated_aliases"].items():
        lines.append(f"- `{target}`: {', '.join(f'`{alias}`' for alias in aliases)}")
    lines.extend(["", "## Rejected controls", ""])
    for item in report["rejected_controls"]:
        lines.append(
            f"- `{item['source_label']}` → `{item['target_field']}`: "
            f"activated={item['activated']}; {item['reason']}"
        )
    lines.extend(["", "## Snapshot invariant", ""])
    for name, evidence in report["old_task_invariant"]["artifacts"].items():
        lines.append(
            f"- {name}: bytes={evidence['bytes_unchanged']}, "
            f"structure={evidence['structure_unchanged']}"
        )
    return "\n".join(lines) + "\n"


def write_reports(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / REPORT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / REPORT_MD).write_text(render_markdown(report), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, default=DECISIONS_PATH)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    try:
        report = run_evaluation(
            decisions_path=args.decisions,
            output_dir=args.output_dir,
        )
    except (FileNotFoundError, LookupError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
