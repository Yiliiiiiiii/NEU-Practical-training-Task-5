import type { KnowledgeLoopApiResponse } from "../types";

export type KnowledgeComparisonPanelProps = {
  result: KnowledgeLoopApiResponse | null;
};

export function KnowledgeComparisonPanel({ result }: KnowledgeComparisonPanelProps) {
  if (!result) {
    return <div className="empty-state">Knowledge-loop 报告尚未加载。</div>;
  }
  if (result.status === "unavailable") {
    return (
      <div className="evidence-panel knowledge-comparison-panel">
        <p className="quiet">Knowledge-loop 证据暂不可用。</p>
        <code>{result.recommended_command}</code>
      </div>
    );
  }
  const report = result.report;
  return (
    <div className="evidence-panel knowledge-comparison-panel">
      <div className="evidence-panel-head">
        <span>已通过 {report?.approved_candidates ?? 0}</span>
        <span>已拒绝 {report?.rejected_candidates ?? 0}</span>
        <span>badcase 违规 {report?.badcase_violation_count ?? 0}</span>
      </div>
      <table>
        <thead>
          <tr><th>阶段</th><th>自动映射</th><th>Review</th><th>缺失</th></tr>
        </thead>
        <tbody>
          <tr><td>之前</td><td>{report?.before.auto_mapped_fields}</td><td>{report?.before.review_required_count}</td><td>{report?.before.missing_required_count}</td></tr>
          <tr><td>之后</td><td>{report?.after.auto_mapped_fields}</td><td>{report?.after.review_required_count}</td><td>{report?.after.missing_required_count}</td></tr>
        </tbody>
      </table>
    </div>
  );
}
