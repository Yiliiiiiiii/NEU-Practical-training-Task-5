import json

from app.schemas.canonical import CanonicalField, CanonicalModel
from app.schemas.mapping import FieldCandidate
from app.schemas.mapping_template import MappingTemplate
from app.schemas.package import Manifest, ManifestFile
from app.schemas.reports import MappingReport
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.uir import UIRBlock, UIRDocument, UIRSource
from app.services.lineage_graph_service import LineageGraphService


def build_graph():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_1",
        source=UIRSource(source_type="external_uir", source_name="fixture"),
        metadata={"domain": "policy_doc"},
        blocks=[
            UIRBlock(
                block_id="b1",
                type="paragraph",
                text="标题：可信转换",
                attributes={"external_path": "payload.blocks[0]"},
            ),
            UIRBlock(block_id="b2", type="paragraph", text="正文"),
        ],
    )
    candidates = [
        FieldCandidate(
            candidate_id="cand_title",
            task_id="task_1",
            doc_id="doc_1",
            source_path="$.blocks.b1.text",
            source_name="标题",
            value_sample="可信转换",
            inferred_type="string",
            source_blocks=["b1"],
            confidence=0.96,
            evidence=["key-value candidate"],
        ),
        FieldCandidate(
            candidate_id="cand_danger",
            task_id="task_1",
            doc_id="doc_1",
            source_path="$.blocks.b2.text",
            source_name="成文日期",
            value_sample="2026-07-05",
            inferred_type="date",
            source_blocks=["b2"],
            confidence=0.65,
            evidence=["date candidate"],
        ),
    ]
    mapping_report = MappingReport(
        task_id="task_1",
        schema_id="policy_doc",
        summary={"badcase_blocked_count": 1},
        mappings=[
            {
                "mapping_id": "map_title",
                "task_id": "task_1",
                "candidate_id": "cand_title",
                "source_field": {
                    "source_path": "$.blocks.b1.text",
                    "source_name": "标题",
                },
                "target_field_id": "title",
                "target_field_name": "标题",
                "method": "alias",
                "confidence": 0.96,
                "confidence_tier": "high",
                "status": "accepted",
                "source_blocks": ["b1"],
                "evidence": [{"type": "alias_match", "message": "alias matched"}],
                "risk_flags": [],
                "badcase_filter": {"checked": True, "blocked": False, "reason": None},
            }
        ],
        review_required_items=[
            {
                "mapping_id": "map_publish_date",
                "task_id": "task_1",
                "candidate_id": "cand_danger",
                "source_field": {
                    "source_path": "$.blocks.b2.text",
                    "source_name": "成文日期",
                },
                "target_field_id": "publish_date",
                "target_field_name": "发布日期",
                "method": "fuzzy",
                "confidence": 0.65,
                "confidence_tier": "low",
                "status": "review_required",
                "need_review": True,
                "source_blocks": ["b2"],
                "evidence": [
                    {
                        "type": "badcase_filter",
                        "message": "forbidden mapping blocked",
                    }
                ],
                "risk_flags": ["badcase_blocked"],
                "badcase_filter": {
                    "checked": True,
                    "blocked": True,
                    "reason": "known badcase",
                },
                "review_required_reason": "Known badcase blocks automatic acceptance.",
            }
        ],
    )
    schema = TargetSchema(
        schema_id="policy_doc",
        name="Policy",
        version="1.0.0",
        fields=[
            TargetField(
                field_id="title",
                name="标题",
                display_name="标题",
                type="string",
                required=True,
            ),
            TargetField(
                field_id="publish_date",
                name="发布日期",
                display_name="发布日期",
                type="date",
            ),
            TargetField(
                field_id="issuer",
                name="发布机构",
                display_name="发布机构",
                type="string",
            ),
        ],
    )
    template = MappingTemplate(
        template_id="policy_doc_base_v1",
        schema_id="policy_doc",
        name="Policy template",
        version="1.0.0",
    )
    canonical = CanonicalModel(
        canonical_version="1.0",
        task_id="task_1",
        doc_id="doc_1",
        schema_id="policy_doc",
        fields={
            "title": CanonicalField(
                value="可信转换",
                type="string",
                source_candidates=["cand_title"],
                source_blocks=["b1"],
            )
        },
    )
    manifest = Manifest(
        manifest_version="1.1",
        package_id="pkg_task_1",
        package_version="1.0.0",
        task_id="task_1",
        doc_id="doc_1",
        created_at="2026-07-05T00:00:00+00:00",
        files=[
            ManifestFile(
                path="content.json",
                required=True,
                media_type="application/json",
                sha256="a" * 64,
                bytes=100,
                role="structured_json",
            ),
            ManifestFile(
                path="chunks.jsonl",
                required=True,
                media_type="application/jsonl",
                sha256="b" * 64,
                bytes=200,
                role="chunks",
            ),
        ],
        generator={
            "name": "SchemaPack Agent",
            "version": "test",
            "schema_id": "policy_doc",
            "schema_version": "1.0.0",
            "template_id": "policy_doc_base_v1",
        },
    )
    return LineageGraphService().build(
        task_id="task_1",
        doc_id="doc_1",
        uir=uir,
        candidates=candidates,
        mapping_report=mapping_report,
        schema=schema,
        template=template,
        canonical=canonical,
        chunks=[
            {
                "chunk_id": "chunk_1",
                "text": "可信转换",
                "source_block_ids": ["b1"],
                "title_path": ["可信转换"],
                "summary": "摘要",
                "keywords": ["可信"],
                "tags": {"quality": "high"},
            }
        ],
        manifest=manifest,
        adapter_report={
            "adapter_id": "block_list",
            "adapter_version": "1.0",
            "trace_items": [
                {
                    "external_path": "payload.blocks[0].text",
                    "canonical_path": "blocks[0].text",
                    "target_block_id": "b1",
                    "conversion_rule": "preserve text",
                    "source_value_preview": "标题：可信转换",
                    "strategy": "rule",
                    "confidence": 1.0,
                    "evidence": ["text preserved"],
                    "review_required": False,
                }
            ],
            "llm_auto_accepted_count": 0,
        },
        review_decisions=[
            {
                "review_id": "review_1",
                "mapping_id": "map_publish_date",
                "candidate_id": "cand_danger",
                "target_field_id": "publish_date",
                "status": "pending",
                "decision": "pending",
                "reason": "Known badcase blocks automatic acceptance.",
            }
        ],
        knowledge_records=[
            {
                "record_type": "candidate",
                "candidate_id": "knowledge_1",
                "review_id": "review_1",
                "target_field_id": "publish_date",
                "status": "blocked",
                "badcase_hit": True,
                "alias": "成文日期",
            },
            {
                "record_type": "pack",
                "pack_id": "pack_active",
                "target_field_id": "title",
                "status": "active",
                "version": "1.0.0",
            },
            {
                "record_type": "pack",
                "pack_id": "pack_draft",
                "target_field_id": "title",
                "status": "draft",
                "version": "1.1.0",
            },
        ],
        applied_knowledge_pack_ids=["pack_active"],
    )


def node_by_id(graph, node_id: str):
    return next(node for node in graph.nodes if node.node_id == node_id)


def test_builds_uir_block_nodes() -> None:
    graph = build_graph()

    node = node_by_id(graph, "lineage:uir_block:b1")

    assert node.metadata["external_path"] == "payload.blocks[0]"
    assert node.metadata["text_preview"] == "标题：可信转换"


def test_links_candidates_to_blocks() -> None:
    graph = build_graph()

    assert any(
        edge.source_node_id == "lineage:uir_block:b1"
        and edge.target_node_id == "lineage:field_candidate:cand_title"
        for edge in graph.edges
    )


def test_links_mapping_decisions_to_schema_fields() -> None:
    graph = build_graph()

    assert any(
        edge.source_node_id == "lineage:mapping_decision:map_title"
        and edge.target_node_id == "lineage:schema_field:title"
        and edge.edge_type == "mapped_to"
        for edge in graph.edges
    )


def test_badcase_blocked_mapping_is_visible() -> None:
    graph = build_graph()

    node = node_by_id(graph, "lineage:mapping_decision:map_publish_date")

    assert node.status == "blocked"
    assert "badcase_blocked" in node.risk_flags
    assert graph.summary["badcase_blocked_count"] == 1


def test_review_required_mapping_is_visible() -> None:
    graph = build_graph()

    review = node_by_id(graph, "lineage:review_decision:review_1")

    assert review.status == "review_required"
    assert any(
        edge.source_node_id == "lineage:mapping_decision:map_publish_date"
        and edge.target_node_id == review.node_id
        for edge in graph.edges
    )


def test_external_adapter_and_knowledge_states_are_visible() -> None:
    graph = build_graph()

    assert any(node.node_type == "external_field" for node in graph.nodes)
    assert any(node.node_type == "adapter_trace" for node in graph.nodes)
    assert node_by_id(graph, "lineage:knowledge_pack:pack_active").status == "accepted"
    assert node_by_id(graph, "lineage:knowledge_pack:pack_draft").status == "informational"
    assert node_by_id(graph, "lineage:knowledge_pack:knowledge_1").status == "blocked"


def test_package_manifest_entries_are_linked() -> None:
    graph = build_graph()

    entry = node_by_id(graph, "lineage:package_manifest_entry:content.json")

    assert entry.metadata["sha256"] == "a" * 64
    assert entry.metadata["role"] == "structured_json"
    assert any(
        edge.source_node_id == "lineage:rendered_artifact:content.json"
        and edge.target_node_id == entry.node_id
        for edge in graph.edges
    )


def test_chunk_links_source_block_and_artifact() -> None:
    graph = build_graph()

    assert any(
        edge.source_node_id == "lineage:uir_block:b1"
        and edge.target_node_id == "lineage:chunk:chunk_1"
        for edge in graph.edges
    )
    assert any(
        edge.source_node_id == "lineage:chunk:chunk_1"
        and edge.target_node_id == "lineage:rendered_artifact:chunks.jsonl"
        for edge in graph.edges
    )


def test_no_secret_like_values_in_lineage_metadata() -> None:
    graph = build_graph()
    unsafe_graph = LineageGraphService().sanitize_graph_payload(
        {
            **graph.model_dump(mode="json"),
            "summary": {
                "api_key": "sk-secret-value",
                "note": "Authorization: Bearer hidden-token",
            },
        }
    )
    serialized = json.dumps(unsafe_graph, ensure_ascii=False).lower()

    assert "sk-secret-value" not in serialized
    assert "hidden-token" not in serialized
    assert '"api_key"' not in serialized


def test_graph_has_no_broken_edges() -> None:
    graph = build_graph()
    node_ids = {node.node_id for node in graph.nodes}

    assert all(
        edge.source_node_id in node_ids and edge.target_node_id in node_ids
        for edge in graph.edges
    )


def test_optional_field_without_source_has_explicit_absence_decision() -> None:
    graph = build_graph()

    node = node_by_id(
        graph,
        "lineage:mapping_decision:source_not_present_issuer",
    )

    assert node.status == "informational"
    assert node.metadata["decision"] == "source_not_present"
    assert graph.summary["field_lineage_coverage"] == 1.0
