from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.schemas.common import StrictBaseModel

LineageNodeType = Literal[
    "external_field",
    "adapter_trace",
    "uir_block",
    "field_candidate",
    "mapping_decision",
    "review_decision",
    "knowledge_pack",
    "schema_field",
    "canonical_field",
    "metadata_source",
    "metadata_field",
    "summary_sentence",
    "tag_trace",
    "upstream_entity",
    "entity_tag",
    "markdown_block",
    "structured_field",
    "rendered_artifact",
    "chunk",
    "package_manifest_entry",
    "consumer_contract",
]

LineageEdgeType = Literal[
    "derived_from",
    "converted_to",
    "candidate_for",
    "mapped_to",
    "reviewed_by",
    "influenced_by",
    "validated_against",
    "rendered_as",
    "contained_in",
    "verified_by",
]

LineageStatus = Literal[
    "accepted",
    "review_required",
    "blocked",
    "failed",
    "warning",
    "informational",
]


class LineageEvidence(StrictBaseModel):
    evidence_id: str
    evidence_type: Literal[
        "source_text",
        "source_path",
        "adapter_trace",
        "candidate_value",
        "mapping_evidence",
        "review_note",
        "knowledge_rule",
        "manifest_hash",
        "contract_check",
    ]
    text: str | None = None
    path: str | None = None
    block_id: str | None = None
    artifact_path: str | None = None
    sha256: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineageNode(StrictBaseModel):
    node_id: str
    node_type: LineageNodeType
    label: str
    status: LineageStatus = "informational"
    doc_id: str | None = None
    task_id: str | None = None
    schema_id: str | None = None
    schema_version: str | None = None
    template_id: str | None = None
    template_version: str | None = None
    field_name: str | None = None
    block_id: str | None = None
    chunk_id: str | None = None
    artifact_path: str | None = None
    confidence: float | None = None
    confidence_tier: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    review_required_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineageEdge(StrictBaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: LineageEdgeType
    confidence: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineageGraph(StrictBaseModel):
    graph_id: str
    doc_id: str
    task_id: str | None = None
    package_id: str | None = None
    schema_id: str | None = None
    template_id: str | None = None
    generated_at: str
    lineage_version: str = "1.0"
    nodes: list[LineageNode]
    edges: list[LineageEdge]
    evidence: list[LineageEvidence]
    summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class LineageQueryResult(StrictBaseModel):
    root_node_id: str
    direction: Literal["upstream", "downstream", "both"]
    max_depth: int
    nodes: list[LineageNode]
    edges: list[LineageEdge]
    evidence: list[LineageEvidence]
    summary: dict[str, Any] = Field(default_factory=dict)
