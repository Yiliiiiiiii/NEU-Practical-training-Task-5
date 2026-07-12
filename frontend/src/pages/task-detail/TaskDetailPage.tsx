import { useEffect, useState } from "react";

import { api } from "../../api";
import { LineagePanel } from "../../components/LineagePanel";
import { PageState } from "../../components/feedback/PageState";
import { StatusBadge } from "../../components/status/StatusBadge";
import type {
  AuditLogListResponse,
  ChunksReport,
  ContentOrganizationReport,
  MappingReport,
  PackageManifest,
  PackageMetadata,
  TaskDetailResponse,
  ValidationReport,
  VerifierReport
} from "../../types";
import { ContentTab } from "./ContentTab";
import { ExecutionTab } from "./ExecutionTab";
import { MappingTab } from "./MappingTab";
import { PackageTab } from "./PackageTab";
import { ValidationTab } from "./ValidationTab";

type Tab = "overview" | "mapping" | "validation" | "content" | "package" | "lineage" | "execution";
type ReportState<T> = { loading: boolean; data: T | null; error?: string };

const tabs: Array<{ id: Tab; label: string }> = [
  { id: "overview", label: "概览" },
  { id: "mapping", label: "映射" },
  { id: "validation", label: "验证" },
  { id: "content", label: "内容" },
  { id: "package", label: "Package" },
  { id: "lineage", label: "谱系" },
  { id: "execution", label: "执行" }
];

function pending<T>(): ReportState<T> {
  return { loading: true, data: null };
}

function isReady(verifier: VerifierReport | null) {
  return verifier?.passed === true;
}

export function TaskDetailPage({ taskId }: { taskId: string }) {
  const [task, setTask] = useState<TaskDetailResponse | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [taskLoading, setTaskLoading] = useState(true);
  const [taskError, setTaskError] = useState("");
  const [mapping, setMapping] = useState<ReportState<MappingReport>>(pending);
  const [validation, setValidation] = useState<ReportState<ValidationReport>>(pending);
  const [contentOrganization, setContentOrganization] = useState<ReportState<ContentOrganizationReport>>(pending);
  const [chunks, setChunks] = useState<ReportState<ChunksReport>>(pending);
  const [manifest, setManifest] = useState<ReportState<PackageManifest>>(pending);
  const [verifier, setVerifier] = useState<ReportState<VerifierReport>>(pending);
  const [packageMetadata, setPackageMetadata] = useState<ReportState<PackageMetadata>>(pending);
  const [auditLogs, setAuditLogs] = useState<ReportState<AuditLogListResponse>>(pending);

  useEffect(() => {
    let active = true;
    setTask(null);
    setTaskLoading(true);
    setTaskError("");
    setMapping(pending());
    setValidation(pending());
    setContentOrganization(pending());
    setChunks(pending());
    setManifest(pending());
    setVerifier(pending());
    setPackageMetadata(pending());
    setAuditLogs(pending());

    void api.listAuditLogs(taskId)
      .then((data) => active && setAuditLogs({ loading: false, data }))
      .catch((caught) => active && setAuditLogs({
        loading: false,
        data: null,
        error: caught instanceof Error ? caught.message : "审计记录读取失败。"
      }));

    void api.getTask(taskId)
      .then((result) => {
        if (!active) return;
        setTask(result);
        setTaskLoading(false);
        void api.getMappingReport(taskId).then((data) => active && setMapping({ loading: false, data })).catch(() => active && setMapping({ loading: false, data: null }));
        void api.getValidationReport(taskId).then((data) => active && setValidation({ loading: false, data })).catch(() => active && setValidation({ loading: false, data: null }));
        void api.getContentOrganizationReport(taskId).then((data) => active && setContentOrganization({ loading: false, data })).catch(() => active && setContentOrganization({ loading: false, data: null }));
        void api.getChunksReport(taskId).then((data) => active && setChunks({ loading: false, data })).catch(() => active && setChunks({ loading: false, data: null }));
        void api.getManifestReport(taskId).then((data) => active && setManifest({ loading: false, data })).catch(() => active && setManifest({ loading: false, data: null }));
        void api.getVerifierReport(taskId).then((data) => active && setVerifier({ loading: false, data })).catch(() => active && setVerifier({ loading: false, data: null }));
        void api.getPackage(taskId).then((data) => active && setPackageMetadata({ loading: false, data })).catch(() => active && setPackageMetadata({ loading: false, data: null }));
      })
      .catch((caught) => {
        if (!active) return;
        setTaskError(caught instanceof Error ? caught.message : "任务读取失败。");
        setTaskLoading(false);
        setMapping({ loading: false, data: null });
        setValidation({ loading: false, data: null });
        setContentOrganization({ loading: false, data: null });
        setChunks({ loading: false, data: null });
        setManifest({ loading: false, data: null });
        setVerifier({ loading: false, data: null });
        setPackageMetadata({ loading: false, data: null });
      });
    return () => { active = false; };
  }, [taskId]);

  function moveTab(event: React.KeyboardEvent<HTMLButtonElement>, index: number) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    setActiveTab(tabs[next].id);
    document.getElementById(`task-tab-${tabs[next].id}`)?.focus();
  }

  return (
    <section className="route-placeholder task-detail-page" aria-labelledby="task-detail-title">
      <p className="page-eyebrow">任务</p>
      <h1 id="task-detail-title">任务详情</h1>
      {taskLoading ? <PageState kind="loading" title="正在读取任务" /> : null}
      {taskError ? <PageState kind="error" title="任务读取失败" detail={taskError} /> : null}
      {task ? (
        <>
          <header className="task-detail-header">
            <dl>
              <div><dt>任务</dt><dd>{task.task_id}</dd></div>
              <div><dt>状态</dt><dd><StatusBadge status={task.status} /></dd></div>
              <div><dt>文档</dt><dd>{task.doc_id}</dd></div>
              <div><dt>Schema</dt><dd>{task.schema_id} / {task.schema_version}</dd></div>
              <div><dt>模板</dt><dd>{task.template_id} / {task.template_version}</dd></div>
            </dl>
          </header>
          <div className="task-detail-tabs" role="tablist" aria-label="任务详情标签">
            {tabs.map((tab, index) => (
              <button
                key={tab.id}
                id={`task-tab-${tab.id}`}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls={`task-panel-${tab.id}`}
                tabIndex={activeTab === tab.id ? 0 : -1}
                onClick={() => setActiveTab(tab.id)}
                onKeyDown={(event) => moveTab(event, index)}
              >{tab.label}</button>
            ))}
          </div>
          <div id={`task-panel-${activeTab}`} className={`task-detail-panel task-detail-panel-${activeTab}`} role="tabpanel" aria-labelledby={`task-tab-${activeTab}`}>
            {activeTab === "overview" ? (
              <section className="task-detail-overview" aria-labelledby="task-overview-title">
                <h2 id="task-overview-title">运行就绪度</h2>
                <dl>
                  <div><dt>任务状态</dt><dd>{task.status}</dd></div>
                  <div><dt>映射报告</dt><dd>{mapping.loading ? "正在读取" : mapping.data ? "可用" : "未生成"}</dd></div>
                  <div><dt>Validation</dt><dd>{validation.loading ? "正在读取" : validation.data?.passed ? "已通过" : validation.data ? "需要处理" : "未生成"}</dd></div>
                  <div><dt>Package 验证器</dt><dd>{verifier.loading ? "正在读取" : verifier.data?.passed ? "已通过" : verifier.data ? "未通过" : "未生成"}</dd></div>
                  <div><dt>下载就绪</dt><dd>{isReady(verifier.data) ? "已就绪" : "未就绪"}</dd></div>
                </dl>
              </section>
            ) : null}
            {activeTab === "mapping" ? <MappingTab report={mapping.data} loading={mapping.loading} /> : null}
            {activeTab === "validation" ? <ValidationTab report={validation.data} loading={validation.loading} /> : null}
            {activeTab === "content" ? <ContentTab organization={contentOrganization.data} chunks={chunks.data} loading={contentOrganization.loading || chunks.loading} /> : null}
            {activeTab === "package" ? <PackageTab taskId={task.task_id} manifest={manifest.data} verifier={verifier.data} packageMetadata={packageMetadata.data} loading={manifest.loading || verifier.loading || packageMetadata.loading} packageDownloadUrl={api.packageDownloadUrl} /> : null}
            {activeTab === "lineage" ? <LineagePanel taskId={task.task_id} available={Boolean(task.report_paths.lineage_graph || task.report_paths.lineage)} /> : null}
            {activeTab === "execution" ? (
              <ExecutionTab
                task={task}
                auditLogs={auditLogs.data?.items ?? null}
                auditLoading={auditLogs.loading}
                auditError={auditLogs.error}
              />
            ) : null}
          </div>
        </>
      ) : null}
    </section>
  );
}
