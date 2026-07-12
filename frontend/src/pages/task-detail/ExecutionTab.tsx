import type { TaskDetailResponse } from "../../types";

function recordText(value: unknown) {
  return value === undefined || value === null ? "—" : typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

export function ExecutionTab({ task }: { task: TaskDetailResponse }) {
  const options = task.options ?? {};
  const audit = options.audit ?? options.audit_log ?? "API 未返回审计字段。";
  const fingerprints = options.fingerprints ?? options.fingerprint ?? "API 未返回 fingerprint 字段。";
  const reason = "当前 API 未提供重放或重新验证端点。";

  return (
    <section className="task-detail-execution-tab" aria-labelledby="execution-detail-title">
      <h2 id="execution-detail-title">执行记录</h2>
      <section aria-labelledby="execution-options-title"><h3 id="execution-options-title">选项</h3><pre>{recordText(options)}</pre></section>
      <section aria-labelledby="execution-audit-title"><h3 id="execution-audit-title">审计</h3><pre>{recordText(audit)}</pre></section>
      <section aria-labelledby="execution-reports-title">
        <h3 id="execution-reports-title">报告路径</h3>
        {Object.keys(task.report_paths).length ? <pre>{recordText(task.report_paths)}</pre> : <p>任务结果未记录报告路径。</p>}
      </section>
      <section aria-labelledby="execution-fingerprint-title"><h3 id="execution-fingerprint-title">Fingerprint 与哈希</h3><p>输入 SHA-256：{task.input_hash}</p><pre>{recordText(fingerprints)}</pre></section>
      <div className="task-detail-execution-actions">
        <button type="button" disabled aria-describedby="execution-action-reason">重放</button>
        <button type="button" disabled aria-describedby="execution-action-reason">重新验证</button>
        <p id="execution-action-reason">{reason}</p>
      </div>
    </section>
  );
}
