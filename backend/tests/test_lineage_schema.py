import pytest
from pydantic import ValidationError

from app.schemas.lineage import (
    LineageEdge,
    LineageEvidence,
    LineageGraph,
    LineageNode,
    LineageQueryResult,
)


@pytest.mark.parametrize(
    "node_type",
    [
        "external_field",
        "adapter_trace",
        "uir_block",
        "field_candidate",
        "mapping_decision",
        "review_decision",
        "knowledge_pack",
        "schema_field",
        "canonical_field",
        "rendered_artifact",
        "chunk",
        "package_manifest_entry",
        "consumer_contract",
    ],
)
def test_lineage_node_schema_accepts_expected_types(node_type: str) -> None:
    node = LineageNode(
        node_id=f"lineage:{node_type}:one",
        node_type=node_type,
        label=node_type,
        status="informational",
    )

    assert node.node_type == node_type


def test_lineage_edge_rejects_missing_source_or_target() -> None:
    with pytest.raises(ValidationError):
        LineageEdge(
            edge_id="edge:one",
            target_node_id="lineage:target",
            edge_type="derived_from",
        )

    with pytest.raises(ValidationError):
        LineageEdge(
            edge_id="edge:two",
            source_node_id="lineage:source",
            edge_type="derived_from",
        )


def test_lineage_graph_and_query_result_round_trip() -> None:
    source = LineageNode(
        node_id="lineage:uir_block:b1",
        node_type="uir_block",
        label="paragraph b1",
        block_id="b1",
    )
    target = LineageNode(
        node_id="lineage:chunk:c1",
        node_type="chunk",
        label="c1",
        chunk_id="c1",
    )
    evidence = LineageEvidence(
        evidence_id="evidence:b1",
        evidence_type="source_text",
        text="safe preview",
        block_id="b1",
    )
    edge = LineageEdge(
        edge_id="edge:b1:c1",
        source_node_id=source.node_id,
        target_node_id=target.node_id,
        edge_type="derived_from",
        evidence_ids=[evidence.evidence_id],
    )
    graph = LineageGraph(
        graph_id="lineage_task_1",
        doc_id="doc_1",
        task_id="task_1",
        generated_at="2026-07-05T00:00:00+00:00",
        nodes=[source, target],
        edges=[edge],
        evidence=[evidence],
    )

    result = LineageQueryResult(
        root_node_id=target.node_id,
        direction="upstream",
        max_depth=8,
        nodes=graph.nodes,
        edges=graph.edges,
        evidence=graph.evidence,
    )

    assert LineageGraph.model_validate(graph.model_dump()).graph_id == graph.graph_id
    assert result.root_node_id == target.node_id
