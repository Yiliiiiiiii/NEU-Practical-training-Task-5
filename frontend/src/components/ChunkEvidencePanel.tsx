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
    return <div className="empty-state">No chunk evidence yet.</div>;
  }
  return (
    <div className="evidence-panel chunk-evidence-panel">
      <div className="filter-bar">
        <select value={strategy} onChange={(event) => setStrategy(event.target.value)}>
          <option value="all">all strategies</option>
          {strategies.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
        <label><input type="checkbox" checked={tablesOnly} onChange={(event) => setTablesOnly(event.target.checked)} /> tables</label>
        <label><input type="checkbox" checked={flaggedOnly} onChange={(event) => setFlaggedOnly(event.target.checked)} /> flagged</label>
      </div>
      <p className="quiet">Showing {chunks.length} of {report.total} chunks.</p>
      {chunks.slice(0, 8).map((chunk) => (
        <details className="chunk-card" key={chunk.chunk_id}>
          <summary>
            <strong>{chunk.chunk_id}</strong>
            <span>{chunk.strategy ?? "legacy"} / {chunk.granularity ?? "chunk"}</span>
          </summary>
          {chunk.parent_chunk_id ? <small>Parent: {chunk.parent_chunk_id}</small> : null}
          <p>{chunk.summary || chunk.text.slice(0, 260)}</p>
          <div className="pill-row">
            {(chunk.content_tags ?? chunk.tags?.content ?? []).map((tag) => <span key={tag}>{tag}</span>)}
            {(chunk.quality_flags?.length ? chunk.quality_flags : chunk.quality_tags ?? []).map((tag) => <span key={tag}>{tag}</span>)}
          </div>
          <small>Sources: {(chunk.source_block_ids ?? []).join(", ") || "none"}</small>
        </details>
      ))}
    </div>
  );
}
