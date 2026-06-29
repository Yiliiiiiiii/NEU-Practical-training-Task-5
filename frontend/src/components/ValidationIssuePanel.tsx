import { suggestedAction } from "../evidence";
import type { ValidationReport } from "../types";

export type ValidationIssuePanelProps = { report: ValidationReport | null };

export function ValidationIssuePanel({ report }: ValidationIssuePanelProps) {
  if (!report) {
    return <div className="empty-state">No validation report yet.</div>;
  }
  return (
    <div className="evidence-panel validation-evidence-panel">
      <div className={report.passed ? "pass-line" : "fail-line"}>
        {report.passed ? "Validation passed" : "Validation needs attention"}
      </div>
      {report.issues.length ? (
        report.issues.map((issue, index) => (
          <article className="issue-row evidence-issue" key={`${String(issue.code)}-${index}`}>
            <span>{String(issue.level ?? issue.severity ?? "issue")}</span>
            <p>{String(issue.message ?? "Validation issue")}</p>
            <small>{suggestedAction(issue)}</small>
          </article>
        ))
      ) : (
        <p className="quiet">No validation issues.</p>
      )}
    </div>
  );
}
