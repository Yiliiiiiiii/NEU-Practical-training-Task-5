import { PageState } from "../../components/feedback/PageState";
import { DataTable } from "../../components/tables/DataTable";
import type { AuditLogListResponse, TaskDetailResponse } from "../../types";

function recordText(value: unknown) {
  return value === undefined || value === null ? "—" : typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

type ExecutionTabProps = {
  task: TaskDetailResponse;
  auditLogs: AuditLogListResponse | null;
  auditLoading: boolean;
  auditLoadingMore: boolean;
  auditError?: string;
  onLoadMore: () => void;
};

export function ExecutionTab({ task, auditLogs, auditLoading, auditLoadingMore, auditError, onLoadMore }: ExecutionTabProps) {
  const options = task.options ?? {};
  const fingerprints = options.fingerprints ?? options.fingerprint ?? "API 未返回 fingerprint 字段。";
  const reason = "当前 API 未提供重放或重新验证端点。";

  return (
    <section className="task-detail-execution-tab" aria-labelledby="execution-detail-title">
      <h2 id="execution-detail-title">执行记录</h2>
      <section aria-labelledby="execution-options-title"><h3 id="execution-options-title">选项</h3><pre>{recordText(options)}</pre></section>
      <section aria-labelledby="execution-audit-title">
        <h3 id="execution-audit-title">审计事件</h3>
        {auditLoading ? <PageState kind="loading" title="正在读取审计事件" /> : null}
        {auditError ? <PageState kind="error" title="审计事件读取失败" detail={auditError} /> : null}
        {!auditLoading && !auditError && !auditLogs?.items.length ? <PageState kind="empty" title="暂无审计事件" /> : null}
        {!auditLoading && auditLogs?.items.length ? (
          <>
            <p>已显示 {auditLogs.items.length} / 共 {auditLogs.total} 条审计事件</p>
            <DataTable label="任务审计事件">
              <table>
                <thead><tr><th>时间</th><th>动作</th><th>结果</th><th>请求</th><th>元数据</th></tr></thead>
                <tbody>
                  {auditLogs.items.map((entry) => (
                    <tr key={entry.audit_id}>
                      <td>{entry.created_at}</td>
                      <td>{entry.action}</td>
                      <td>{entry.success ? "成功" : "失败"}{entry.status_code ? ` (${entry.status_code})` : ""}</td>
                      <td>{[entry.method, entry.path].filter(Boolean).join(" ") || "—"}</td>
                      <td><pre>{recordText(entry.metadata)}</pre></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </DataTable>
            {auditLogs.items.length < auditLogs.total ? (
              <button type="button" onClick={onLoadMore} disabled={auditLoadingMore}>
                {auditLoadingMore ? "正在加载审计事件" : "加载更多审计事件"}
              </button>
            ) : null}
          </>
        ) : null}
      </section>
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
