import { useMemo, useState } from "react";

import { filterChunks } from "../evidence";
import type { ChunksReport } from "../types";

export type ChunkEvidencePanelProps = { report: ChunksReport | null };

export function ChunkEvidencePanel({ report }: ChunkEvidencePanelProps) {
  const [strategy, setStrategy] = useState("all");
  const [tablesOnly, setTablesOnly] = useState(false);
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const strategies = useMemo(
    () =>
      Array.from(
        new Set(
          (report?.items ?? [])
            .map((chunk) => chunk.strategy)
            .filter((item): item is string => Boolean(item))
        )
      ),
    [report]
  );
  const chunks = filterChunks(report?.items ?? [], { strategy, tablesOnly, flaggedOnly });
  if (!report) {
    return <div className="empty-state">暂无 Chunk 证据。</div>;
  }
  return (
    <div className="evidence-panel chunk-evidence-panel">
      <div className="filter-bar">
        <select value={strategy} onChange={(event) => setStrategy(event.target.value)}>
          <option value="all">全部策略</option>
          {strategies.map((item) => (
            <option key={item} value={item}>
              {displayChunkStrategy(item)}
            </option>
          ))}
        </select>
        <label><input type="checkbox" checked={tablesOnly} onChange={(event) => setTablesOnly(event.target.checked)} /> 仅表格</label>
        <label><input type="checkbox" checked={flaggedOnly} onChange={(event) => setFlaggedOnly(event.target.checked)} /> 仅标记项</label>
      </div>
      <p className="quiet">显示 {chunks.length} 个，共 {report.total} 个 Chunk。</p>
      {chunks.slice(0, 8).map((chunk) => (
        <details className="chunk-card" key={chunk.chunk_id}>
          <summary>
            <strong>{chunk.chunk_id}</strong>
            <span>
              {displayChunkStrategy(chunk.strategy)} / {displayChunkGranularity(chunk.granularity)}
            </span>
          </summary>
          {chunk.parent_chunk_id ? <small>父 Chunk: {chunk.parent_chunk_id}</small> : null}
          <p>{chunk.summary || chunk.text.slice(0, 260)}</p>
          <div className="pill-row">
            {(chunk.content_tags ?? chunk.tags?.content ?? []).map((tag) => <span key={tag}>{tag}</span>)}
            {(chunk.quality_flags?.length ? chunk.quality_flags : chunk.quality_tags ?? []).map((tag) => <span key={tag}>{tag}</span>)}
          </div>
          <small>来源: {(chunk.source_block_ids ?? []).join(", ") || "无"}</small>
        </details>
      ))}
    </div>
  );
}

function displayChunkStrategy(strategy: string | null | undefined) {
  const labels: Record<string, string> = {
    fixed_window: "固定窗口",
    heading_aware: "标题感知",
    source_block_aware: "源块感知",
    table_protect: "表格保护",
    parent_child: "父子 Chunk",
    legacy: "旧策略"
  };
  return strategy ? labels[strategy] ?? strategy : "旧策略";
}

function displayChunkGranularity(granularity: string | null | undefined) {
  const labels: Record<string, string> = {
    chunk: "Chunk",
    paragraph: "段落",
    section: "章节",
    table: "表格"
  };
  return granularity ? labels[granularity] ?? granularity : "Chunk";
}
