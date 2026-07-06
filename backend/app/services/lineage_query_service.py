from __future__ import annotations

from collections import defaultdict, deque
from typing import Literal

from app.schemas.lineage import LineageGraph, LineageQueryResult

LineageDirection = Literal["upstream", "downstream", "both"]


class LineageQueryService:
    def query_field(
        self,
        graph: LineageGraph,
        field_name: str,
        *,
        direction: LineageDirection = "upstream",
        max_depth: int = 8,
    ) -> LineageQueryResult:
        root = next(
            (
                node
                for node in graph.nodes
                if node.node_type == "canonical_field"
                and node.field_name == field_name
            ),
            None,
        )
        if root is None:
            root = next(
                (
                    node
                    for node in graph.nodes
                    if node.node_type == "schema_field"
                    and node.field_name == field_name
                ),
                None,
            )
        if root is None:
            raise LookupError("lineage root not found")
        return self.query(
            graph,
            root.node_id,
            direction=direction,
            max_depth=max_depth,
        )

    def query_chunk(
        self,
        graph: LineageGraph,
        chunk_id: str,
        *,
        direction: LineageDirection = "upstream",
        max_depth: int = 8,
    ) -> LineageQueryResult:
        root = next(
            (
                node
                for node in graph.nodes
                if node.node_type == "chunk" and node.chunk_id == chunk_id
            ),
            None,
        )
        if root is None:
            raise LookupError("lineage root not found")
        return self.query(
            graph,
            root.node_id,
            direction=direction,
            max_depth=max_depth,
        )

    def query_artifact(
        self,
        graph: LineageGraph,
        artifact_path: str,
        *,
        direction: LineageDirection = "both",
        max_depth: int = 8,
    ) -> LineageQueryResult:
        root = next(
            (
                node
                for node in graph.nodes
                if node.node_type == "package_manifest_entry"
                and node.artifact_path == artifact_path
            ),
            None,
        )
        if root is None:
            root = next(
                (
                    node
                    for node in graph.nodes
                    if node.node_type == "rendered_artifact"
                    and node.artifact_path == artifact_path
                ),
                None,
            )
        if root is None:
            raise LookupError("lineage root not found")
        return self.query(
            graph,
            root.node_id,
            direction=direction,
            max_depth=max_depth,
        )

    def query(
        self,
        graph: LineageGraph,
        root_node_id: str,
        *,
        direction: LineageDirection = "both",
        max_depth: int = 8,
    ) -> LineageQueryResult:
        if direction not in {"upstream", "downstream", "both"}:
            raise ValueError("unsupported lineage direction")
        if not 1 <= max_depth <= 32:
            raise ValueError("max_depth must be between 1 and 32")

        nodes_by_id = {node.node_id: node for node in graph.nodes}
        if root_node_id not in nodes_by_id:
            raise LookupError("lineage root not found")

        incoming = defaultdict(list)
        outgoing = defaultdict(list)
        for edge in graph.edges:
            incoming[edge.target_node_id].append(edge)
            outgoing[edge.source_node_id].append(edge)

        selected_node_ids = {root_node_id}
        selected_edge_ids: set[str] = set()
        queue = deque([(root_node_id, 0)])
        while queue:
            node_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            candidate_edges = []
            if direction in {"upstream", "both"}:
                candidate_edges.extend(
                    (edge, edge.source_node_id) for edge in incoming[node_id]
                )
            if direction in {"downstream", "both"}:
                candidate_edges.extend(
                    (edge, edge.target_node_id) for edge in outgoing[node_id]
                )
            for edge, adjacent_node_id in candidate_edges:
                selected_edge_ids.add(edge.edge_id)
                if adjacent_node_id in selected_node_ids:
                    continue
                selected_node_ids.add(adjacent_node_id)
                queue.append((adjacent_node_id, depth + 1))

        selected_edges = [
            edge for edge in graph.edges if edge.edge_id in selected_edge_ids
        ]
        selected_evidence_ids = {
            evidence_id
            for edge in selected_edges
            for evidence_id in edge.evidence_ids
        }
        selected_nodes = [
            node for node in graph.nodes if node.node_id in selected_node_ids
        ]
        selected_evidence = [
            evidence
            for evidence in graph.evidence
            if evidence.evidence_id in selected_evidence_ids
        ]
        return LineageQueryResult(
            root_node_id=root_node_id,
            direction=direction,
            max_depth=max_depth,
            nodes=selected_nodes,
            edges=selected_edges,
            evidence=selected_evidence,
            summary={
                "node_count": len(selected_nodes),
                "edge_count": len(selected_edges),
                "evidence_count": len(selected_evidence),
            },
        )
