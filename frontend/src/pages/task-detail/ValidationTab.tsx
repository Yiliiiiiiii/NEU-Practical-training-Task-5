import { PageState } from "../../components/feedback/PageState";
import { DataTable } from "../../components/tables/DataTable";
import type { ValidationReport } from "../../types";

type ValidationGroup = {
  severity: string;
  stage: string;
  path: string;
  code: string;
  suggestedAction: string;
  issues: Array<Record<string, any>>;
};

function firstText(issue: Record<string, any>, keys: string[], fallback = "—") {
  for (const key of keys) {
    const value = issue[key];
    if (value !== undefined && value !== null && value !== "") return Array.isArray(value) ? value.join("；") : String(value);
  }
  return fallback;
}

export function ValidationTab({ report, loading }: { report: ValidationReport | null; loading: boolean }) {
  if (loading) return <PageState kind="loading" title="正在读取验证报告" />;
  if (!report) return <PageState kind="empty" title="验证报告尚未生成" detail="任务结果中没有可用的验证报告。" />;
  if (!report.issues.length) return <PageState kind="empty" title={report.passed ? "Validation 已通过，未发现问题" : "验证报告未返回问题明细"} />;

  const grouped = new Map<string, ValidationGroup>();
  report.issues.forEach((issue) => {
    const severity = firstText(issue, ["severity", "level"]);
    const stage = firstText(issue, ["stage", "phase", "validator"]);
    const path = firstText(issue, ["path", "field_path", "location"]);
    const code = firstText(issue, ["code", "rule_id", "type"]);
    const key = [severity, stage, path, code].join("|");
    const current = grouped.get(key) ?? {
      severity,
      stage,
      path,
      code,
      suggestedAction: firstText(issue, ["suggested_action", "action", "remediation", "recommendation"]),
      issues: []
    };
    current.issues.push(issue);
    grouped.set(key, current);
  });

  return (
    <section className="task-detail-validation-tab" aria-labelledby="validation-report-title">
      <h2 id="validation-report-title">Validation 问题</h2>
      <DataTable className="task-detail-validation-table" label="Validation 问题表">
        <table>
          <thead><tr><th>严重级别</th><th>阶段</th><th>路径</th><th>代码</th><th>建议操作</th><th>原始明细</th></tr></thead>
          <tbody>
            {Array.from(grouped.values()).map((group) => (
              <tr key={[group.severity, group.stage, group.path, group.code].join("|")}>
                <td>{group.severity}</td><td>{group.stage}</td><td>{group.path}</td><td>{group.code}</td><td>{group.suggestedAction}</td>
                <td>
                  <details>
                    <summary>{group.issues.length} 条明细</summary>
                    <pre>{JSON.stringify(group.issues, null, 2)}</pre>
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </DataTable>
    </section>
  );
}
