import type { KnowledgeLoopApiResponse } from "../types";

export type KnowledgeComparisonPanelProps = {
  result: KnowledgeLoopApiResponse | null;
};

export function KnowledgeComparisonPanel({ result }: KnowledgeComparisonPanelProps) {
  if (!result) {
    return <div className="empty-state">Knowledge-loop report not loaded.</div>;
  }
  if (result.status === "unavailable") {
    return (
      <div className="evidence-panel knowledge-comparison-panel">
        <p className="quiet">Knowledge-loop evidence is unavailable.</p>
        <code>{result.recommended_command}</code>
      </div>
    );
  }
  const report = result.report;
  return (
    <div className="evidence-panel knowledge-comparison-panel">
      <div className="evidence-panel-head">
        <span>approved {report?.approved_candidates ?? 0}</span>
        <span>rejected {report?.rejected_candidates ?? 0}</span>
        <span>badcases {report?.badcase_violation_count ?? 0}</span>
      </div>
      <table>
        <thead>
          <tr><th>Stage</th><th>Auto mapped</th><th>Review</th><th>Missing</th></tr>
        </thead>
        <tbody>
          <tr><td>Before</td><td>{report?.before.auto_mapped_fields}</td><td>{report?.before.review_required_count}</td><td>{report?.before.missing_required_count}</td></tr>
          <tr><td>After</td><td>{report?.after.auto_mapped_fields}</td><td>{report?.after.review_required_count}</td><td>{report?.after.missing_required_count}</td></tr>
        </tbody>
      </table>
    </div>
  );
}
