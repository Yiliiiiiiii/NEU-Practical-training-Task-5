import { useEffect, useState } from "react";

import { PageState } from "../../components/feedback/PageState";
import type { ChunksReport, ContentOrganizationReport } from "../../types";

function tagList(chunk: Record<string, any>) {
  const nested = chunk.tags ?? {};
  return [
    ...(chunk.content_tags ?? nested.content ?? []),
    ...(chunk.management_tags ?? nested.management ?? []),
    ...(chunk.quality_tags ?? nested.quality ?? []),
    ...(chunk.quality_flags ?? [])
  ].map(String);
}

export function ContentTab({
  organization,
  chunks,
  loading,
  error
}: {
  organization: ContentOrganizationReport | null;
  chunks: ChunksReport | null;
  loading: boolean;
  error?: string;
}) {
  const [selectedId, setSelectedId] = useState("");
  const items = chunks?.items ?? [];

  useEffect(() => {
    setSelectedId(items[0]?.chunk_id ?? "");
  }, [chunks]);

  if (loading) return <PageState kind="loading" title="正在读取内容报告" />;
  if (error) return <PageState kind="error" title="内容报告读取失败" detail={error} />;
  if (!organization && !chunks) return <PageState kind="empty" title="内容报告尚未生成" detail="任务结果中没有可用的内容组织或 Chunk 报告。" />;
  if (!items.length) return <PageState kind="empty" title="内容报告未包含 Chunk" />;

  const selected = items.find((chunk) => chunk.chunk_id === selectedId) ?? items[0];
  const selectedRecord = selected as Record<string, any>;
  const entities = selectedRecord.entities ?? selectedRecord.entity_mentions ?? [];

  return (
    <section className="task-detail-content-tab" aria-labelledby="content-report-title">
      <h2 id="content-report-title">内容组织</h2>
      <label>
        选择 Chunk
        <select value={selected.chunk_id} onChange={(event) => setSelectedId(event.target.value)}>
          {items.map((chunk) => <option key={chunk.chunk_id} value={chunk.chunk_id}>{chunk.chunk_id}</option>)}
        </select>
      </label>
      <dl>
        <div><dt>策略</dt><dd>{selected.strategy ?? "—"}</dd></div>
        <div><dt>标签</dt><dd>{tagList(selectedRecord).join("；") || "—"}</dd></div>
        <div><dt>摘要</dt><dd>{selected.summary ?? "—"}</dd></div>
        <div><dt>实体</dt><dd>{Array.isArray(entities) ? entities.map((item) => typeof item === "string" ? item : JSON.stringify(item)).join("；") || "—" : String(entities)}</dd></div>
      </dl>
      <details>
        <summary>Chunk 原文</summary>
        <pre>{selected.text}</pre>
      </details>
    </section>
  );
}
