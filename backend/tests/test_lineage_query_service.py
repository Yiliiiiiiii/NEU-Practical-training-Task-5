import pytest

from app.services.lineage_query_service import LineageQueryService
from tests.test_lineage_graph_service import build_graph


def test_query_field_lineage_upstream() -> None:
    result = LineageQueryService().query_field(
        build_graph(),
        "title",
        direction="upstream",
        max_depth=8,
    )
    node_ids = {node.node_id for node in result.nodes}

    assert result.root_node_id == "lineage:canonical_field:title"
    assert "lineage:mapping_decision:map_title" in node_ids
    assert "lineage:field_candidate:cand_title" in node_ids
    assert "lineage:uir_block:b1" in node_ids


def test_query_chunk_lineage_upstream() -> None:
    result = LineageQueryService().query_chunk(
        build_graph(),
        "chunk_1",
        direction="upstream",
        max_depth=8,
    )

    assert result.root_node_id == "lineage:chunk:chunk_1"
    assert "lineage:uir_block:b1" in {node.node_id for node in result.nodes}


def test_query_artifact_lineage_downstream() -> None:
    result = LineageQueryService().query_artifact(
        build_graph(),
        "content.json",
        direction="downstream",
        max_depth=8,
    )
    node_ids = {node.node_id for node in result.nodes}

    assert result.root_node_id == "lineage:package_manifest_entry:content.json"
    assert "lineage:consumer_contract:package-1.1" in node_ids


def test_query_artifact_both_includes_sources_and_contract() -> None:
    result = LineageQueryService().query_artifact(
        build_graph(),
        "content.json",
        direction="both",
        max_depth=8,
    )
    node_ids = {node.node_id for node in result.nodes}

    assert "lineage:canonical_field:title" in node_ids
    assert "lineage:consumer_contract:package-1.1" in node_ids


def test_query_respects_max_depth() -> None:
    result = LineageQueryService().query_field(
        build_graph(),
        "title",
        direction="upstream",
        max_depth=1,
    )

    assert "lineage:schema_field:title" in {node.node_id for node in result.nodes}
    assert "lineage:uir_block:b1" not in {node.node_id for node in result.nodes}


@pytest.mark.parametrize(
    ("method", "value"),
    [
        ("query_field", "unknown"),
        ("query_chunk", "unknown"),
        ("query_artifact", "unknown.json"),
    ],
)
def test_unknown_query_root_raises_lookup_error(method: str, value: str) -> None:
    with pytest.raises(LookupError, match="lineage root not found"):
        getattr(LineageQueryService(), method)(build_graph(), value)
