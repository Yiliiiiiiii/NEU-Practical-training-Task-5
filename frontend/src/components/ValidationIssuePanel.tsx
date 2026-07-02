import { suggestedAction } from "../evidence";
import type { ValidationReport } from "../types";

export type ValidationIssuePanelProps = { report: ValidationReport | null };

export function ValidationIssuePanel({ report }: ValidationIssuePanelProps) {
  if (!report) {
    return <div className="empty-state">暂无 Validation 报告。</div>;
  }
  return (
    <div className="evidence-panel validation-evidence-panel">
      <div className={report.passed ? "pass-line" : "fail-line"}>
        {report.passed ? "Validation 已通过" : "Validation 需要处理"}
      </div>
      {report.issues.length ? (
        report.issues.map((issue, index) => (
          <article className="issue-row evidence-issue" key={`${String(issue.code)}-${index}`}>
            <span>{String(issue.level ?? issue.severity ?? "issue")}</span>
            <p>{String(issue.message ?? "Validation 问题")}</p>
            <small>{suggestedAction(issue)}</small>
          </article>
        ))
      ) : (
        <p className="quiet">暂无 Validation 问题。</p>
      )}
    </div>
  );
}
