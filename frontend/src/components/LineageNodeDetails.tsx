import type { LineageEvidence, LineageNode } from "../types";

type LineageNodeDetailsProps = {
  node: LineageNode | null;
  evidence: LineageEvidence[];
};

export function LineageNodeDetails({
  node,
  evidence
}: LineageNodeDetailsProps) {
  if (!node) {
    return (
      <aside className="lineage-node-details lineage-node-details-empty">
        选择链路节点查看证据。
      </aside>
    );
  }
  const relevantEvidence = evidence.filter((item) =>
    item.block_id === node.block_id ||
    item.artifact_path === node.artifact_path ||
    node.node_id.includes(item.evidence_id.split(":").at(-1) ?? "")
  );
  return (
    <aside className="lineage-node-details" aria-label="Lineage 节点详情">
      <p className="lineage-kicker">{node.node_type.replaceAll("_", " ")}</p>
      <h4>{node.label}</h4>
      <dl>
        {node.field_name ? <Detail label="字段" value={node.field_name} /> : null}
        {node.block_id ? <Detail label="Block" value={node.block_id} /> : null}
        {node.chunk_id ? <Detail label="Chunk" value={node.chunk_id} /> : null}
        {node.artifact_path ? (
          <Detail label="Artifact" value={node.artifact_path} />
        ) : null}
        {typeof node.confidence === "number" ? (
          <Detail label="置信度" value={`${Math.round(node.confidence * 100)}%`} />
        ) : null}
      </dl>
      {node.review_required_reason ? (
        <p className="lineage-review-reason">{node.review_required_reason}</p>
      ) : null}
      {node.risk_flags.length ? (
        <div className="lineage-risk-list">
          {node.risk_flags.map((flag) => <span key={flag}>{flag}</span>)}
        </div>
      ) : null}
      <details>
        <summary>Metadata</summary>
        <pre>{JSON.stringify(node.metadata, null, 2)}</pre>
      </details>
      {relevantEvidence.length ? (
        <details>
          <summary>Evidence · {relevantEvidence.length}</summary>
          <ul>
            {relevantEvidence.map((item) => (
              <li key={item.evidence_id}>{item.text ?? item.path ?? item.evidence_type}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </aside>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
