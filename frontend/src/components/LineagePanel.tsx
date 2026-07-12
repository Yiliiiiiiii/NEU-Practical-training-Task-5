import { useEffect, useMemo, useState } from "react";

import { api } from "../api";
import type {
  LineageGraph,
  LineageNode,
  LineageQueryResult,
  LineageSummary
} from "../types";
import { LineageGraphView } from "./LineageGraphView";
import { LineageNodeDetails } from "./LineageNodeDetails";

type QueryKind = "field" | "chunk" | "artifact";

type LineagePanelProps = {
  taskId: string;
  available: boolean;
};

export function LineagePanel({ taskId, available }: LineagePanelProps) {
  const [graph, setGraph] = useState<LineageGraph | null>(null);
  const [summary, setSummary] = useState<LineageSummary | null>(null);
  const [queryResult, setQueryResult] = useState<LineageQueryResult | null>(null);
  const [queryKind, setQueryKind] = useState<QueryKind>("field");
  const [rootValue, setRootValue] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!taskId || !available) {
      setGraph(null);
      setSummary(null);
      setQueryResult(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError("");
    void Promise.all([api.getLineage(taskId), api.getLineageSummary(taskId)])
      .then(([nextGraph, nextSummary]) => {
        if (cancelled) return;
        setGraph(nextGraph);
        setSummary(nextSummary);
        const firstField = rootsFor(nextGraph.nodes, "field")[0];
        setRootValue(firstField?.value ?? "");
        setSelectedNodeId(firstField?.nodeId ?? nextGraph.nodes[0]?.node_id ?? "");
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Unknown lineage error");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [taskId, available]);

  const roots = useMemo(
    () => rootsFor(graph?.nodes ?? [], queryKind),
    [graph, queryKind]
  );
  const display = queryResult ?? graph;
  const selectedNode =
    display?.nodes.find((node) => node.node_id === selectedNodeId) ??
    display?.nodes[0] ??
    null;

  function changeKind(nextKind: QueryKind) {
    setQueryKind(nextKind);
    setQueryResult(null);
    const first = rootsFor(graph?.nodes ?? [], nextKind)[0];
    setRootValue(first?.value ?? "");
    setSelectedNodeId(first?.nodeId ?? "");
  }

  async function runQuery() {
    if (!taskId || !rootValue) return;
    setLoading(true);
    setError("");
    try {
      const result =
        queryKind === "field"
          ? await api.getFieldLineage(taskId, rootValue, "upstream", 8)
          : queryKind === "chunk"
            ? await api.getChunkLineage(taskId, rootValue, "upstream", 8)
            : await api.getArtifactLineage(taskId, rootValue, "both", 8);
      setQueryResult(result);
      setSelectedNodeId(result.root_node_id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown lineage error");
    } finally {
      setLoading(false);
    }
  }

  if (!taskId || !available) {
    return <div className="empty-state">Task 执行完成后可查看可信链路。</div>;
  }
  if (error && !graph) {
    return (
      <div className="lineage-error" role="alert">
        <strong>Lineage 暂时不可用</strong>
        <span>{error}</span>
      </div>
    );
  }
  if (!graph || !summary) {
    return <div className="empty-state">{loading ? "正在装配证据链…" : "暂无 Lineage。"}</div>;
  }

  return (
    <section className="lineage-panel">
      <div className="lineage-summary-grid">
        <SummaryCard label="总覆盖率" value={summary.lineage_coverage} />
        <SummaryCard label="字段覆盖率" value={summary.field_lineage_coverage} />
        <SummaryCard label="Chunk 覆盖率" value={summary.chunk_lineage_coverage} />
        <SummaryCard label="Artifact 覆盖率" value={summary.artifact_lineage_coverage} />
      </div>

      <div className="lineage-facts" aria-label="Lineage 状态摘要">
        <span>{summary.review_required_count} 个待 Review</span>
        <span>{summary.badcase_blocked_count} 个已阻断</span>
        <span>{summary.knowledge_influenced_count} 个知识影响</span>
        <span>{summary.source_mode}</span>
      </div>

      <div className="lineage-query-bar">
        <label>
          查询类型
          <select
            value={queryKind}
            onChange={(event) => changeKind(event.target.value as QueryKind)}
          >
            <option value="field">目标字段</option>
            <option value="chunk">Chunk</option>
            <option value="artifact">Artifact</option>
          </select>
        </label>
        <label>
          查询对象
          <select
            value={rootValue}
            onChange={(event) => setRootValue(event.target.value)}
          >
            {roots.map((root) => (
              <option key={root.nodeId} value={root.value}>{root.label}</option>
            ))}
          </select>
        </label>
        <button type="button" onClick={() => void runQuery()} disabled={loading || !rootValue}>
          {loading ? "查询中…" : "查询链路"}
        </button>
        {queryResult ? (
          <button type="button" onClick={() => setQueryResult(null)}>查看全图</button>
        ) : null}
      </div>

      {error ? <div className="lineage-inline-error">{error}</div> : null}

      <div className="lineage-workbench">
        <LineageGraphView
          nodes={display?.nodes ?? []}
          edges={display?.edges ?? []}
          selectedNodeId={selectedNodeId}
          onSelect={setSelectedNodeId}
        />
        <LineageNodeDetails
          node={selectedNode}
          evidence={display?.evidence ?? []}
        />
      </div>

      <p className="lineage-semantic-warning">
        Lineage 证明来源、证据和决策链路可追溯；它不等同于字段语义严格正确。请同时查看
        Validation、Review、Badcase 和 Evaluation 报告。
      </p>
    </section>
  );
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="lineage-summary-card">
      <span>{label}</span>
      <strong>{Math.round(value * 100)}%</strong>
    </div>
  );
}

function rootsFor(nodes: LineageNode[], kind: QueryKind) {
  const seen = new Set<string>();
  return nodes.flatMap((node) => {
    const value =
      kind === "field" && node.node_type === "schema_field"
        ? node.field_name
        : kind === "chunk" && node.node_type === "chunk"
          ? node.chunk_id
          : kind === "artifact" && node.node_type === "package_manifest_entry"
            ? node.artifact_path
            : null;
    if (!value || seen.has(value)) return [];
    seen.add(value);
    return [{ value, label: node.label, nodeId: node.node_id }];
  });
}
