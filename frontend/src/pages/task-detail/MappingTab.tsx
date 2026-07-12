import { PageState } from "../../components/feedback/PageState";
import { DataTable } from "../../components/tables/DataTable";
import type { MappingReport } from "../../types";

type MappingRow = Record<string, any> & { collection: "mapped" | "review" | "unmapped" };

function text(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  if (Array.isArray(value)) return value.map((item) => text(item, "")).filter(Boolean).join("；") || fallback;
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function valueOf(row: MappingRow, keys: string[]) {
  for (const key of keys) {
    if (row[key] !== undefined && row[key] !== null && row[key] !== "") return row[key];
  }
  return undefined;
}

function statusLabel(row: MappingRow) {
  const flags = Array.isArray(row.risk_flags) ? row.risk_flags.map(String) : [];
  const status = String(row.status ?? "").toLowerCase();
  const llmSuggested = Boolean(
    row.llm_metadata || row.suggested_by === "llm" || row.method === "llm_fallback" || flags.includes("llm_suggestion")
  );
  if (row.collection === "unmapped" || status === "unmapped") return "未映射";
  if (status === "blocked" || flags.includes("badcase_blocked") || flags.includes("blocked")) return "已阻断";
  if (llmSuggested && row.auto_accepted !== true) return "LLM 建议（未自动采纳）";
  if (row.collection === "review" || row.review_required === true || status === "review_required") return "需要复核";
  return "自动采纳";
}

export function MappingTab({ report, loading }: { report: MappingReport | null; loading: boolean }) {
  if (loading) return <PageState kind="loading" title="正在读取映射报告" />;
  if (!report) return <PageState kind="empty" title="映射报告尚未生成" detail="任务结果中没有可用的映射报告。" />;

  const rows: MappingRow[] = [
    ...report.mappings.map((row) => ({ ...row, collection: "mapped" as const })),
    ...report.review_required_items.map((row) => ({ ...row, collection: "review" as const })),
    ...report.unmapped.map((row) => ({ ...row, collection: "unmapped" as const }))
  ];
  if (!rows.length) return <PageState kind="empty" title="映射报告暂无记录" />;

  return (
    <section className="task-detail-mapping-tab" aria-labelledby="mapping-report-title">
      <h2 id="mapping-report-title">映射报告</h2>
      <DataTable className="task-detail-mapping-table" label="映射报告表">
        <table>
          <thead>
            <tr><th>来源候选</th><th>来源路径</th><th>目标字段</th><th>置信度</th><th>证据</th><th>风险</th><th>备选</th><th>状态</th></tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={`${String(valueOf(row, ["mapping_id", "candidate_id", "target_field_id"]) ?? "row")}-${index}`}>
                <td>{text(valueOf(row, ["source_candidate", "source_field_name", "source_name", "candidate_id"]))}</td>
                <td>{text(valueOf(row, ["source_path", "candidate_path", "path"]))}</td>
                <td>{text(valueOf(row, ["target_field", "target_field_id", "target_field_name"]))}</td>
                <td>{text(valueOf(row, ["confidence", "score", "final_score"]))}</td>
                <td>{text(valueOf(row, ["evidence", "evidence_text", "evidence_items"]))}</td>
                <td>{text(valueOf(row, ["risk_flags", "risk", "review_required_reason"]))}</td>
                <td>{text(valueOf(row, ["alternatives", "top_alternatives", "candidate_alternatives"]))}</td>
                <td>{statusLabel(row)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </DataTable>
    </section>
  );
}
