from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.canonical import CanonicalModel
from app.schemas.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageEvidence,
    LineageGraph,
    LineageNode,
)
from app.schemas.mapping import FieldCandidate
from app.schemas.mapping_template import MappingTemplate
from app.schemas.package import Manifest
from app.schemas.reports import MappingReport
from app.schemas.target_schema import TargetSchema
from app.schemas.uir import UIRDocument

_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "credential",
    "credentials",
    "deepseek_api_key",
    "llm_api_key",
    "password",
    "secret",
    "token",
}
_SENSITIVE_SUFFIXES = ("_api_key", "_password", "_secret", "_token")
_SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(?:\b(?:authorization|bearer|api[_-]?key|password|secret|token)\b|"
    r"\bsk-[a-z0-9_-]{4,})"
)


class LineageGraphService:
    def __init__(self) -> None:
        self._nodes: dict[str, LineageNode] = {}
        self._edges: dict[str, LineageEdge] = {}
        self._evidence: dict[str, LineageEvidence] = {}
        self._task_id = ""
        self._doc_id = ""

    def build(
        self,
        *,
        task_id: str,
        doc_id: str,
        uir: UIRDocument,
        candidates: Sequence[FieldCandidate],
        mapping_report: MappingReport,
        schema: TargetSchema,
        template: MappingTemplate,
        canonical: CanonicalModel,
        chunks: Sequence[dict[str, Any]],
        manifest: Manifest,
        adapter_report: BaseModel | Mapping[str, Any] | None = None,
        review_decisions: Sequence[Mapping[str, Any]] = (),
        knowledge_records: Sequence[Mapping[str, Any]] = (),
        applied_knowledge_pack_ids: Sequence[str] = (),
    ) -> LineageGraph:
        self._nodes = {}
        self._edges = {}
        self._evidence = {}
        self._task_id = task_id
        self._doc_id = doc_id

        self._add_uir_blocks(uir)
        self._add_candidates(candidates)
        self._add_schema_fields(schema, template)
        self._add_mappings(mapping_report, schema)
        self._add_reviews(review_decisions)
        self._add_knowledge(knowledge_records, set(applied_knowledge_pack_ids))
        self._add_canonical(canonical)
        self._add_chunks(chunks)
        self._add_manifest(manifest)

        warnings: list[str] = []
        source_mode = "standard_uir"
        if adapter_report is not None:
            source_mode = "external_uir"
            self._add_adapter_report(self._as_dict(adapter_report))
        else:
            warnings.append("source_mode=standard_uir; no External UIR adapter trace is available.")

        nodes = sorted(self._nodes.values(), key=lambda item: item.node_id)
        edges = sorted(self._edges.values(), key=lambda item: item.edge_id)
        evidence = sorted(self._evidence.values(), key=lambda item: item.evidence_id)
        summary = self._summary(
            nodes=nodes,
            edges=edges,
            schema=schema,
            chunks=chunks,
            manifest=manifest,
            source_mode=source_mode,
        )
        return LineageGraph(
            graph_id=f"lineage_{task_id}",
            doc_id=doc_id,
            task_id=task_id,
            package_id=manifest.package_id,
            schema_id=schema.schema_id,
            template_id=template.template_id,
            generated_at=datetime.now(UTC).isoformat(),
            nodes=nodes,
            edges=edges,
            evidence=evidence,
            summary=self._safe_metadata(summary),
            warnings=warnings,
        )

    @classmethod
    def sanitize_graph_payload(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): cls.sanitize_graph_payload(item)
                for key, item in value.items()
                if not cls._is_sensitive_key(str(key))
            }
        if isinstance(value, list | tuple):
            return [cls.sanitize_graph_payload(item) for item in value]
        if isinstance(value, str) and _SECRET_VALUE_PATTERN.search(value):
            return "[REDACTED]"
        return value

    def _add_uir_blocks(self, uir: UIRDocument) -> None:
        for block in uir.blocks:
            node_id = self._node_id("uir_block", block.block_id)
            metadata: dict[str, Any] = {
                "block_type": block.type,
                "level": block.level,
                "text_preview": (block.text or "")[:120],
            }
            if block.source_anchor is not None:
                metadata["source_anchor"] = block.source_anchor.model_dump(mode="json")
            external_path = block.attributes.get("external_path")
            if isinstance(external_path, str):
                metadata["external_path"] = external_path
            self._add_node(
                LineageNode(
                    node_id=node_id,
                    node_type="uir_block",
                    label=self._safe_text(f"{block.type} {block.block_id}"),
                    task_id=self._task_id,
                    doc_id=self._doc_id,
                    block_id=block.block_id,
                    metadata=self._safe_metadata(metadata),
                )
            )
            if block.text:
                evidence_id = self._evidence_id("source_text", block.block_id)
                self._add_evidence(
                    LineageEvidence(
                        evidence_id=evidence_id,
                        evidence_type="source_text",
                        text=self._safe_text(block.text[:240]),
                        block_id=block.block_id,
                    )
                )

    def _add_candidates(self, candidates: Sequence[FieldCandidate]) -> None:
        for candidate in candidates:
            self._ensure_candidate(
                candidate_id=candidate.candidate_id,
                source_path=candidate.source_path,
                source_name=candidate.source_name,
                value_sample=candidate.value_sample,
                source_blocks=candidate.source_blocks,
                confidence=candidate.confidence,
                metadata={
                    "display_name": candidate.display_name,
                    "inferred_type": candidate.inferred_type,
                    "evidence": candidate.evidence,
                },
            )

    def _ensure_candidate(
        self,
        *,
        candidate_id: str,
        source_path: str,
        source_name: str,
        value_sample: Any,
        source_blocks: Sequence[str],
        confidence: float | None,
        metadata: Mapping[str, Any] | None = None,
    ) -> str:
        node_id = self._node_id("field_candidate", candidate_id)
        if node_id not in self._nodes:
            self._add_node(
                LineageNode(
                    node_id=node_id,
                    node_type="field_candidate",
                    label=self._safe_text(source_name or candidate_id),
                    status="informational",
                    task_id=self._task_id,
                    doc_id=self._doc_id,
                    confidence=confidence,
                    metadata=self._safe_metadata(
                        {
                            "source_path": source_path,
                            "source_name": source_name,
                            "value_preview": self._preview(value_sample),
                            **dict(metadata or {}),
                        }
                    ),
                )
            )
            evidence_id = self._evidence_id("candidate_value", candidate_id)
            self._add_evidence(
                LineageEvidence(
                    evidence_id=evidence_id,
                    evidence_type="candidate_value",
                    text=self._safe_text(self._preview(value_sample)),
                    path=self._safe_text(source_path),
                    metadata=self._safe_metadata({"source_name": source_name}),
                )
            )
        for block_id in source_blocks:
            block_node_id = self._node_id("uir_block", block_id)
            if block_node_id in self._nodes:
                self._add_edge(
                    block_node_id,
                    node_id,
                    "candidate_for",
                    evidence_ids=[self._evidence_id("candidate_value", candidate_id)],
                )
        return node_id

    def _add_schema_fields(
        self,
        schema: TargetSchema,
        template: MappingTemplate,
    ) -> None:
        for field in schema.fields:
            self._add_node(
                LineageNode(
                    node_id=self._node_id("schema_field", field.field_id),
                    node_type="schema_field",
                    label=self._safe_text(field.display_name or field.name),
                    status="informational",
                    task_id=self._task_id,
                    doc_id=self._doc_id,
                    schema_id=schema.schema_id,
                    schema_version=schema.version,
                    template_id=template.template_id,
                    template_version=template.version,
                    field_name=field.field_id,
                    metadata=self._safe_metadata(
                        {
                            "field_id": field.field_id,
                            "name": field.name,
                            "type": field.type,
                            "required": field.required,
                        }
                    ),
                )
            )

    def _add_mappings(
        self,
        report: MappingReport,
        schema: TargetSchema,
    ) -> None:
        items = [
            *report.mappings,
            *report.review_required_items,
            *report.unmapped,
        ]
        represented_fields: set[str] = set()
        for index, item in enumerate(items):
            mapping_id = str(
                item.get("mapping_id")
                or f"unmapped_{item.get('target_field_id', index)}"
            )
            target_field_id = str(item.get("target_field_id") or "")
            if target_field_id:
                represented_fields.add(target_field_id)
            risk_flags = [
                str(flag)
                for flag in item.get("risk_flags", [])
                if isinstance(flag, str)
            ]
            blocked = bool(
                item.get("badcase_filter", {}).get("blocked")
                if isinstance(item.get("badcase_filter"), Mapping)
                else False
            ) or "badcase_blocked" in risk_flags
            status = (
                "blocked"
                if blocked
                else "accepted"
                if item.get("status") == "accepted"
                else "failed"
                if item.get("status") == "failed"
                else "review_required"
            )
            mapping_node_id = self._node_id("mapping_decision", mapping_id)
            self._add_node(
                LineageNode(
                    node_id=mapping_node_id,
                    node_type="mapping_decision",
                    label=self._safe_text(
                        f"{item.get('source_field_name') or self._source_name(item) or 'unmapped'}"
                        f" -> {target_field_id or 'unknown'}"
                    ),
                    status=status,
                    task_id=self._task_id,
                    doc_id=self._doc_id,
                    schema_id=report.schema_id,
                    field_name=target_field_id or None,
                    confidence=self._number(item.get("confidence")),
                    confidence_tier=self._optional_text(item.get("confidence_tier")),
                    risk_flags=risk_flags,
                    review_required_reason=self._optional_safe_text(
                        item.get("review_required_reason")
                    ),
                    metadata=self._safe_metadata(
                        {
                            "mapping_id": mapping_id,
                            "candidate_id": item.get("candidate_id"),
                            "source_path": item.get("source_path")
                            or self._source_path(item),
                            "source_name": self._source_name(item),
                            "target_field_id": target_field_id,
                            "target_field_name": item.get("target_field_name"),
                            "strategy": item.get("strategy") or item.get("method"),
                            "badcase_filter": item.get("badcase_filter", {}),
                            "need_review": bool(item.get("need_review")),
                            "llm_metadata": item.get("llm_metadata"),
                        }
                    ),
                )
            )

            evidence_ids = self._mapping_evidence(mapping_id, item)
            candidate_id = item.get("candidate_id")
            if isinstance(candidate_id, str) and candidate_id:
                candidate_node_id = self._node_id("field_candidate", candidate_id)
                if candidate_node_id not in self._nodes:
                    self._ensure_candidate(
                        candidate_id=candidate_id,
                        source_path=self._source_path(item),
                        source_name=self._source_name(item) or candidate_id,
                        value_sample=item.get("value_sample"),
                        source_blocks=self._string_list(item.get("source_blocks")),
                        confidence=self._number(item.get("confidence")),
                    )
                self._add_edge(
                    candidate_node_id,
                    mapping_node_id,
                    "derived_from",
                    confidence=self._number(item.get("confidence")),
                    evidence_ids=evidence_ids,
                )
            schema_node_id = self._node_id("schema_field", target_field_id)
            if target_field_id and schema_node_id in self._nodes:
                self._add_edge(
                    mapping_node_id,
                    schema_node_id,
                    "mapped_to",
                    confidence=self._number(item.get("confidence")),
                    evidence_ids=evidence_ids,
                )
        for field in schema.fields:
            if field.field_id in represented_fields:
                continue
            mapping_id = f"source_not_present_{field.field_id}"
            mapping_node_id = self._node_id("mapping_decision", mapping_id)
            self._add_node(
                LineageNode(
                    node_id=mapping_node_id,
                    node_type="mapping_decision",
                    label=self._safe_text(f"source not present -> {field.field_id}"),
                    status="informational",
                    task_id=self._task_id,
                    doc_id=self._doc_id,
                    schema_id=report.schema_id,
                    field_name=field.field_id,
                    metadata={
                        "mapping_id": mapping_id,
                        "target_field_id": field.field_id,
                        "required": field.required,
                        "decision": "source_not_present",
                    },
                )
            )
            self._add_edge(
                mapping_node_id,
                self._node_id("schema_field", field.field_id),
                "mapped_to",
                metadata={"decision": "source_not_present"},
            )

    def _mapping_evidence(
        self,
        mapping_id: str,
        item: Mapping[str, Any],
    ) -> list[str]:
        evidence_ids: list[str] = []
        raw_evidence = item.get("evidence", [])
        if not isinstance(raw_evidence, list):
            raw_evidence = []
        for index, entry in enumerate(raw_evidence):
            entry_dict = entry if isinstance(entry, Mapping) else {}
            text = (
                entry_dict.get("message")
                if entry_dict
                else entry
            )
            evidence_id = self._evidence_id("mapping", f"{mapping_id}:{index}")
            self._add_evidence(
                LineageEvidence(
                    evidence_id=evidence_id,
                    evidence_type="mapping_evidence",
                    text=self._safe_text(str(text)),
                    path=self._optional_safe_text(
                        item.get("source_path") or self._source_path(item)
                    ),
                    metadata=self._safe_metadata(dict(entry_dict)),
                )
            )
            evidence_ids.append(evidence_id)
        return evidence_ids

    def _add_reviews(self, reviews: Sequence[Mapping[str, Any]]) -> None:
        for review in reviews:
            review_id = str(review.get("review_id") or "")
            mapping_id = str(review.get("mapping_id") or "")
            if not review_id:
                continue
            raw_status = str(review.get("status") or review.get("decision") or "pending")
            status = (
                "accepted"
                if raw_status == "approved"
                else "blocked"
                if raw_status == "rejected"
                else "review_required"
            )
            node_id = self._node_id("review_decision", review_id)
            self._add_node(
                LineageNode(
                    node_id=node_id,
                    node_type="review_decision",
                    label=self._safe_text(f"Review {review_id}"),
                    status=status,
                    task_id=self._task_id,
                    doc_id=self._doc_id,
                    field_name=self._optional_text(review.get("target_field_id")),
                    confidence=self._number(review.get("confidence")),
                    review_required_reason=self._optional_safe_text(review.get("reason")),
                    metadata=self._safe_metadata(dict(review)),
                )
            )
            evidence_id = self._evidence_id("review", review_id)
            self._add_evidence(
                LineageEvidence(
                    evidence_id=evidence_id,
                    evidence_type="review_note",
                    text=self._safe_text(
                        str(
                            review.get("review_comment")
                            or review.get("comment")
                            or review.get("reason")
                            or raw_status
                        )
                    ),
                )
            )
            mapping_node_id = self._node_id("mapping_decision", mapping_id)
            if mapping_id and mapping_node_id in self._nodes:
                self._add_edge(
                    mapping_node_id,
                    node_id,
                    "reviewed_by",
                    evidence_ids=[evidence_id],
                )

    def _add_knowledge(
        self,
        records: Sequence[Mapping[str, Any]],
        applied_pack_ids: set[str],
    ) -> None:
        for index, record in enumerate(records):
            record_type = str(record.get("record_type") or "pack")
            record_id = str(
                record.get("pack_id")
                or record.get("candidate_id")
                or f"knowledge_{index}"
            )
            raw_status = str(record.get("status") or "draft")
            status = (
                "blocked"
                if raw_status in {"blocked"}
                else "accepted"
                if raw_status == "active" and record_id in applied_pack_ids
                else "informational"
            )
            node_id = self._node_id("knowledge_pack", record_id)
            self._add_node(
                LineageNode(
                    node_id=node_id,
                    node_type="knowledge_pack",
                    label=self._safe_text(f"{record_type} {record_id}"),
                    status=status,
                    task_id=self._task_id,
                    doc_id=self._doc_id,
                    field_name=self._optional_text(record.get("target_field_id")),
                    risk_flags=(
                        ["badcase_blocked"]
                        if bool(record.get("badcase_hit")) or raw_status == "blocked"
                        else []
                    ),
                    metadata=self._safe_metadata(
                        {
                            **dict(record),
                            "applied_to_task": record_id in applied_pack_ids,
                        }
                    ),
                )
            )
            evidence_id = self._evidence_id("knowledge", record_id)
            self._add_evidence(
                LineageEvidence(
                    evidence_id=evidence_id,
                    evidence_type="knowledge_rule",
                    text=self._safe_text(
                        str(record.get("alias") or record.get("name") or raw_status)
                    ),
                    metadata=self._safe_metadata({"status": raw_status}),
                )
            )
            review_id = record.get("review_id")
            review_node_id = self._node_id("review_decision", str(review_id))
            if review_id and review_node_id in self._nodes:
                self._add_edge(
                    review_node_id,
                    node_id,
                    "converted_to",
                    evidence_ids=[evidence_id],
                )
            target_field_id = record.get("target_field_id")
            schema_node_id = self._node_id("schema_field", str(target_field_id))
            if target_field_id and schema_node_id in self._nodes:
                self._add_edge(
                    node_id,
                    schema_node_id,
                    "influenced_by",
                    evidence_ids=[evidence_id],
                )

    def _add_canonical(self, canonical: CanonicalModel) -> None:
        for field_name, field in canonical.fields.items():
            node_id = self._node_id("canonical_field", field_name)
            self._add_node(
                LineageNode(
                    node_id=node_id,
                    node_type="canonical_field",
                    label=self._safe_text(field_name),
                    status="accepted",
                    task_id=self._task_id,
                    doc_id=self._doc_id,
                    schema_id=canonical.schema_id,
                    field_name=field_name,
                    metadata=self._safe_metadata(
                        {
                            "type": field.type,
                            "value_preview": self._preview(field.value),
                            "source_candidates": field.source_candidates,
                            "source_blocks": field.source_blocks,
                        }
                    ),
                )
            )
            schema_node_id = self._node_id("schema_field", field_name)
            if schema_node_id in self._nodes:
                self._add_edge(schema_node_id, node_id, "converted_to")
            for candidate_id in field.source_candidates:
                candidate_node_id = self._node_id("field_candidate", candidate_id)
                if candidate_node_id in self._nodes:
                    self._add_edge(candidate_node_id, node_id, "converted_to")
            for mapping_node in self._nodes.values():
                if (
                    mapping_node.node_type == "mapping_decision"
                    and mapping_node.field_name == field_name
                    and mapping_node.status == "accepted"
                ):
                    self._add_edge(mapping_node.node_id, node_id, "converted_to")

    def _add_chunks(self, chunks: Sequence[dict[str, Any]]) -> None:
        for index, chunk in enumerate(chunks):
            chunk_id = str(chunk.get("chunk_id") or f"chunk_{index}")
            node_id = self._node_id("chunk", chunk_id)
            self._add_node(
                LineageNode(
                    node_id=node_id,
                    node_type="chunk",
                    label=self._safe_text(chunk_id),
                    status="accepted",
                    task_id=self._task_id,
                    doc_id=self._doc_id,
                    chunk_id=chunk_id,
                    metadata=self._safe_metadata(
                        {
                            "title_path": chunk.get("title_path", []),
                            "source_block_ids": chunk.get("source_block_ids", []),
                            "strategy": chunk.get("strategy"),
                            "granularity": chunk.get("granularity"),
                            "summary": chunk.get("summary"),
                            "keywords": chunk.get("keywords", []),
                            "quality_tags": chunk.get("quality_tags")
                            or chunk.get("tags", {}),
                            "text_preview": self._preview(chunk.get("text")),
                        }
                    ),
                )
            )
            for block_id in self._string_list(chunk.get("source_block_ids")):
                block_node_id = self._node_id("uir_block", block_id)
                if block_node_id in self._nodes:
                    self._add_edge(block_node_id, node_id, "derived_from")

    def _add_manifest(self, manifest: Manifest) -> None:
        contract_node_id = self._node_id("consumer_contract", "package-1.1")
        self._add_node(
            LineageNode(
                node_id=contract_node_id,
                node_type="consumer_contract",
                label="Package 1.1 consumer contract",
                status="accepted",
                task_id=self._task_id,
                doc_id=self._doc_id,
                metadata={"manifest_version": manifest.manifest_version},
            )
        )
        for file_info in manifest.files:
            artifact_node_id = self._node_id("rendered_artifact", file_info.path)
            self._add_node(
                LineageNode(
                    node_id=artifact_node_id,
                    node_type="rendered_artifact",
                    label=self._safe_text(file_info.path),
                    status="accepted",
                    task_id=self._task_id,
                    doc_id=self._doc_id,
                    artifact_path=file_info.path,
                    metadata=self._safe_metadata(
                        {
                            "role": file_info.role,
                            "media_type": file_info.media_type,
                        }
                    ),
                )
            )
            entry_node_id = self._node_id("package_manifest_entry", file_info.path)
            self._add_node(
                LineageNode(
                    node_id=entry_node_id,
                    node_type="package_manifest_entry",
                    label=self._safe_text(file_info.path),
                    status="accepted",
                    task_id=self._task_id,
                    doc_id=self._doc_id,
                    artifact_path=file_info.path,
                    metadata=self._safe_metadata(file_info.model_dump(mode="json")),
                )
            )
            evidence_id = self._evidence_id("manifest", file_info.path)
            self._add_evidence(
                LineageEvidence(
                    evidence_id=evidence_id,
                    evidence_type="manifest_hash",
                    artifact_path=file_info.path,
                    sha256=file_info.sha256,
                    metadata=self._safe_metadata(
                        {
                            "role": file_info.role,
                            "required": file_info.required,
                            "bytes": file_info.bytes,
                            "media_type": file_info.media_type,
                        }
                    ),
                )
            )
            self._add_edge(
                artifact_node_id,
                entry_node_id,
                "contained_in",
                evidence_ids=[evidence_id],
            )
            self._add_edge(
                entry_node_id,
                contract_node_id,
                "verified_by",
                evidence_ids=[evidence_id],
            )
            self._link_artifact_sources(file_info.path, artifact_node_id)

    def _link_artifact_sources(self, path: str, artifact_node_id: str) -> None:
        if path == "chunks.jsonl":
            sources = [
                node for node in self._nodes.values() if node.node_type == "chunk"
            ]
        elif path == "mapping_report.json":
            sources = [
                node
                for node in self._nodes.values()
                if node.node_type == "mapping_decision"
            ]
        elif path in {"content.json", "content.md", "canonical.json"}:
            sources = [
                node
                for node in self._nodes.values()
                if node.node_type == "canonical_field"
            ]
            if path == "content.md":
                sources.extend(
                    node
                    for node in self._nodes.values()
                    if node.node_type == "uir_block"
                )
        else:
            sources = []
        for source in sources:
            self._add_edge(source.node_id, artifact_node_id, "rendered_as")

    def _add_adapter_report(self, report: Mapping[str, Any]) -> None:
        adapter_id = str(report.get("adapter_id") or "external_uir")
        trace_items = report.get("trace_items", [])
        if not isinstance(trace_items, list):
            return
        for index, trace in enumerate(trace_items):
            if not isinstance(trace, Mapping):
                continue
            external_path = str(trace.get("external_path") or f"trace[{index}]")
            external_node_id = self._node_id("external_field", external_path)
            trace_id = str(trace.get("trace_id") or f"{adapter_id}:{index}")
            trace_node_id = self._node_id("adapter_trace", trace_id)
            status = "review_required" if trace.get("review_required") else "accepted"
            self._add_node(
                LineageNode(
                    node_id=external_node_id,
                    node_type="external_field",
                    label=self._safe_text(external_path),
                    status="informational",
                    task_id=self._task_id,
                    doc_id=self._doc_id,
                    metadata=self._safe_metadata(
                        {
                            "external_path": external_path,
                            "source_value_preview": trace.get("source_value_preview"),
                        }
                    ),
                )
            )
            self._add_node(
                LineageNode(
                    node_id=trace_node_id,
                    node_type="adapter_trace",
                    label=self._safe_text(
                        str(trace.get("conversion_rule") or trace_id)
                    ),
                    status=status,
                    task_id=self._task_id,
                    doc_id=self._doc_id,
                    confidence=self._number(trace.get("confidence")),
                    metadata=self._safe_metadata(
                        {
                            "adapter_id": adapter_id,
                            "adapter_version": report.get("adapter_version"),
                            **dict(trace),
                        }
                    ),
                )
            )
            evidence_id = self._evidence_id("adapter", trace_id)
            self._add_evidence(
                LineageEvidence(
                    evidence_id=evidence_id,
                    evidence_type="adapter_trace",
                    text=self._safe_text(
                        "; ".join(self._string_list(trace.get("evidence")))
                        or str(trace.get("conversion_rule") or "")
                    ),
                    path=self._safe_text(external_path),
                    block_id=self._optional_text(trace.get("target_block_id")),
                    metadata=self._safe_metadata(
                        {
                            "canonical_path": trace.get("canonical_path"),
                            "strategy": trace.get("strategy"),
                        }
                    ),
                )
            )
            self._add_edge(
                external_node_id,
                trace_node_id,
                "converted_to",
                confidence=self._number(trace.get("confidence")),
                evidence_ids=[evidence_id],
            )
            block_id = trace.get("target_block_id")
            block_node_id = self._node_id("uir_block", str(block_id))
            if block_id and block_node_id in self._nodes:
                self._add_edge(
                    trace_node_id,
                    block_node_id,
                    "converted_to",
                    confidence=self._number(trace.get("confidence")),
                    evidence_ids=[evidence_id],
                )

    def _summary(
        self,
        *,
        nodes: Sequence[LineageNode],
        edges: Sequence[LineageEdge],
        schema: TargetSchema,
        chunks: Sequence[dict[str, Any]],
        manifest: Manifest,
        source_mode: str,
    ) -> dict[str, Any]:
        mapped_fields = {
            node.field_name
            for node in nodes
            if node.node_type == "mapping_decision"
            and node.field_name
        }
        traced_chunks = {
            edge.target_node_id
            for edge in edges
            if edge.target_node_id.startswith("lineage:chunk:")
            and edge.source_node_id.startswith("lineage:uir_block:")
        }
        traced_artifacts = {
            edge.target_node_id
            for edge in edges
            if edge.target_node_id.startswith("lineage:package_manifest_entry:")
            and edge.source_node_id.startswith("lineage:rendered_artifact:")
        }
        field_count = len(schema.fields)
        chunk_count = len(chunks)
        artifact_count = len(manifest.files)
        field_coverage = len(mapped_fields) / field_count if field_count else 1.0
        chunk_coverage = len(traced_chunks) / chunk_count if chunk_count else 1.0
        artifact_coverage = (
            len(traced_artifacts) / artifact_count if artifact_count else 1.0
        )
        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "field_count": field_count,
            "fields_traced": len(mapped_fields),
            "field_lineage_coverage": round(field_coverage, 4),
            "chunk_count": chunk_count,
            "chunks_traced": len(traced_chunks),
            "chunk_lineage_coverage": round(chunk_coverage, 4),
            "artifact_count": artifact_count,
            "artifacts_traced": len(traced_artifacts),
            "artifact_lineage_coverage": round(artifact_coverage, 4),
            "review_required_count": sum(
                node.status == "review_required" for node in nodes
            ),
            "badcase_blocked_count": sum(
                node.node_type == "mapping_decision"
                and node.status == "blocked"
                for node in nodes
            ),
            "knowledge_influenced_count": sum(
                node.node_type == "knowledge_pack" for node in nodes
            ),
            "lineage_coverage": round(
                (field_coverage + chunk_coverage + artifact_coverage) / 3,
                4,
            ),
            "source_mode": source_mode,
        }

    def _add_node(self, node: LineageNode) -> None:
        self._nodes.setdefault(node.node_id, node)

    def _add_evidence(self, evidence: LineageEvidence) -> None:
        self._evidence.setdefault(evidence.evidence_id, evidence)

    def _add_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        edge_type: LineageEdgeType,
        *,
        confidence: float | None = None,
        evidence_ids: Sequence[str] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if source_node_id not in self._nodes or target_node_id not in self._nodes:
            return
        digest = hashlib.sha256(
            f"{source_node_id}|{edge_type}|{target_node_id}".encode()
        ).hexdigest()[:16]
        edge_id = f"lineage:edge:{digest}"
        self._edges.setdefault(
            edge_id,
            LineageEdge(
                edge_id=edge_id,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                edge_type=edge_type,
                confidence=confidence,
                evidence_ids=[
                    evidence_id
                    for evidence_id in evidence_ids
                    if evidence_id in self._evidence
                ],
                metadata=self._safe_metadata(dict(metadata or {})),
            ),
        )

    @staticmethod
    def _node_id(node_type: str, value: str) -> str:
        return f"lineage:{node_type}:{value}"

    @staticmethod
    def _evidence_id(evidence_type: str, value: str) -> str:
        digest = hashlib.sha256(f"{evidence_type}|{value}".encode()).hexdigest()[:16]
        return f"lineage:evidence:{evidence_type}:{digest}"

    @classmethod
    def _safe_metadata(cls, value: Mapping[str, Any]) -> dict[str, Any]:
        sanitized = cls.sanitize_graph_payload(dict(value))
        return sanitized if isinstance(sanitized, dict) else {}

    @classmethod
    def _safe_text(cls, value: str) -> str:
        sanitized = cls.sanitize_graph_payload(value)
        return str(sanitized)

    @classmethod
    def _optional_safe_text(cls, value: Any) -> str | None:
        return cls._safe_text(value) if isinstance(value, str) else None

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _number(value: Any) -> float | None:
        if isinstance(value, bool):
            return None
        return float(value) if isinstance(value, int | float) else None

    @staticmethod
    def _preview(value: Any) -> str:
        if value is None:
            return ""
        return str(value)[:240]

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if not isinstance(value, list | tuple):
            return []
        return [
            str(item)
            for item in value
            if isinstance(item, str | int | float)
        ]

    @staticmethod
    def _source_path(item: Mapping[str, Any]) -> str:
        source = item.get("source_field")
        if isinstance(source, Mapping):
            value = source.get("source_path")
            if isinstance(value, str):
                return value
        value = item.get("source_path")
        return value if isinstance(value, str) else ""

    @staticmethod
    def _source_name(item: Mapping[str, Any]) -> str:
        source = item.get("source_field")
        if isinstance(source, Mapping):
            value = source.get("source_name")
            if isinstance(value, str):
                return value
        value = item.get("source_field_name")
        return value if isinstance(value, str) else ""

    @staticmethod
    def _as_dict(value: BaseModel | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        return dict(value)

    @staticmethod
    def _is_sensitive_key(key: str) -> bool:
        normalized = key.strip().lower().replace("-", "_")
        return normalized in _SENSITIVE_KEYS or normalized.endswith(
            _SENSITIVE_SUFFIXES
        )
