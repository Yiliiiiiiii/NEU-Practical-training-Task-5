import type { LineageEdge, LineageNode } from "../types";

const stageOrder = [
  "external_field",
  "adapter_trace",
  "uir_block",
  "field_candidate",
  "mapping_decision",
  "review_decision",
  "knowledge_pack",
  "schema_field",
  "canonical_field",
  "chunk",
  "rendered_artifact",
  "package_manifest_entry",
  "consumer_contract"
];

const statusLabels: Record<string, string> = {
  accepted: "已接受",
  review_required: "待 Review",
  blocked: "已阻断",
  failed: "失败",
  warning: "警告",
  informational: "信息"
};

type LineageGraphViewProps = {
  nodes: LineageNode[];
  edges: LineageEdge[];
  selectedNodeId: string;
  onSelect: (nodeId: string) => void;
};

export function LineageGraphView({
  nodes,
  edges,
  selectedNodeId,
  onSelect
}: LineageGraphViewProps) {
  const sortedNodes = [...nodes].sort((left, right) => {
    const stage = stageOrder.indexOf(left.node_type) - stageOrder.indexOf(right.node_type);
    return stage || left.label.localeCompare(right.label, "zh-CN");
  });
  const incoming = new Map<string, LineageEdge[]>();
  for (const edge of edges) {
    incoming.set(edge.target_node_id, [...(incoming.get(edge.target_node_id) ?? []), edge]);
  }

  return (
    <div className="lineage-ledger" aria-label="Lineage 分层链路">
      {sortedNodes.map((node) => (
        <button
          type="button"
          className={`lineage-node tone-${node.status} ${
            selectedNodeId === node.node_id ? "is-selected" : ""
          }`}
          key={node.node_id}
          onClick={() => onSelect(node.node_id)}
        >
          <span className="lineage-stage-index">
            {String(Math.max(1, stageOrder.indexOf(node.node_type) + 1)).padStart(2, "0")}
          </span>
          <span className="lineage-node-copy">
            <small>{node.node_type.replaceAll("_", " ")}</small>
            <strong>{node.label}</strong>
            {node.review_required_reason ? <em>{node.review_required_reason}</em> : null}
            {(incoming.get(node.node_id) ?? []).length ? (
              <i>
                {(incoming.get(node.node_id) ?? [])
                  .map((edge) => edge.edge_type.replaceAll("_", " "))
                  .join(" · ")}
              </i>
            ) : null}
          </span>
          <span className="lineage-status">{statusLabels[node.status] ?? node.status}</span>
        </button>
      ))}
    </div>
  );
}
