import { FileJson2, Play, RotateCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import type { ReportResponse, TaskDetailResponse } from "../api/types";
import type { ToastInput, WorkbenchSelection } from "../appTypes";
import { CodePanel } from "../components/CodePanel";
import { ReportTabs, type ReportKey } from "../components/ReportTabs";
import { StatusBadge } from "../components/StatusBadge";

interface TaskDetailPageProps {
  selection: WorkbenchSelection;
  onSelectionChange: (selection: WorkbenchSelection) => void;
  onToast?: (toast: ToastInput) => void;
}

const EMPTY_REPORTS: Record<ReportKey, ReportResponse | null> = {
  mapping: null,
  validation: null,
  consistency: null,
  trace: null,
};

async function optionalReport(request: Promise<ReportResponse>): Promise<ReportResponse | null> {
  try {
    return await request;
  } catch {
    return null;
  }
}

export function TaskDetailPage({
  selection,
  onSelectionChange,
  onToast,
}: TaskDetailPageProps) {
  const [task, setTask] = useState<TaskDetailResponse | null>(null);
  const [canonical, setCanonical] = useState<ReportResponse | null>(null);
  const [reports, setReports] = useState(EMPTY_REPORTS);
  const [isBusy, setIsBusy] = useState(false);
  const taskId = selection.taskId;

  const loadArtifacts = useCallback(async () => {
    if (!taskId) {
      setCanonical(null);
      setReports(EMPTY_REPORTS);
      return;
    }
    const [canonicalResult, mapping, validation, consistency, trace] = await Promise.all([
      optionalReport(api.getCanonical(taskId)),
      optionalReport(api.getMappingReport(taskId)),
      optionalReport(api.getValidationReport(taskId)),
      optionalReport(api.getConsistencyReport(taskId)),
      optionalReport(api.getTrace(taskId)),
    ]);
    setCanonical(canonicalResult);
    setReports({ mapping, validation, consistency, trace });
  }, [taskId]);

  const loadTask = useCallback(async () => {
    if (!taskId) {
      setTask(null);
      return;
    }
    setIsBusy(true);
    try {
      const taskResponse = await api.getTask(taskId);
      setTask(taskResponse);
      onSelectionChange({
        docId: taskResponse.doc_id,
        schemaId: taskResponse.schema_id,
        templateId: taskResponse.template_id,
        taskId: taskResponse.task_id,
        taskStatus: taskResponse.status,
      });
      await loadArtifacts();
    } catch (error) {
      onToast?.({
        tone: "danger",
        title: "Task detail failed",
        detail: error instanceof Error ? error.message : "Unexpected task detail failure.",
      });
    } finally {
      setIsBusy(false);
    }
  }, [loadArtifacts, onSelectionChange, onToast, taskId]);

  useEffect(() => {
    void loadTask();
  }, [loadTask]);

  async function handleConvert() {
    if (!taskId) {
      return;
    }
    setIsBusy(true);
    try {
      const response = await api.convertTask(taskId);
      onSelectionChange({ ...selection, taskStatus: response.status });
      setTask((current) => (current ? { ...current, status: response.status } : current));
      await loadArtifacts();
      onToast?.({
        tone: "success",
        title: "Conversion completed",
        detail: response.outputs.join(", "),
      });
    } catch (error) {
      onToast?.({
        tone: "danger",
        title: "Conversion failed",
        detail: error instanceof Error ? error.message : "Unexpected conversion failure.",
      });
    } finally {
      setIsBusy(false);
    }
  }

  if (!taskId) {
    return (
      <section className="document-panel">
        <div className="empty-state">
          <strong>No task selected.</strong>
          <span>Open a task from Tasks before inspecting canonical output.</span>
        </div>
      </section>
    );
  }

  const conversionBlocked = ["review_required", "failed", "cancelled"].includes(
    task?.status ?? selection.taskStatus ?? "",
  );

  return (
    <section className="document-panel detail-page" aria-labelledby="detail-page-title">
      <div className="document-panel__header">
        <div>
          <span className="section-label">Conversion evidence</span>
          <h2 id="detail-page-title">Task detail</h2>
          <p>Run canonical conversion, inspect provenance, and read each report from the real API.</p>
        </div>
        <div className="button-row">
          <button className="secondary-button" disabled={isBusy} onClick={loadTask} type="button">
            <RotateCw aria-hidden="true" size={15} />
            Refresh
          </button>
          <button
            className="primary-button"
            disabled={isBusy || conversionBlocked}
            onClick={() => void handleConvert()}
            type="button"
          >
            <Play aria-hidden="true" size={15} />
            {isBusy ? "Working..." : "Convert task"}
          </button>
        </div>
      </div>

      <div className="task-facts" aria-label="Task facts">
        <div><span>Task</span><strong>{taskId}</strong></div>
        <div><span>Status</span><StatusBadge status={task?.status ?? selection.taskStatus ?? "created"} /></div>
        <div><span>Document</span><strong>{task?.doc_id ?? selection.docId ?? "-"}</strong></div>
        <div><span>Schema</span><strong>{task?.schema_id ?? selection.schemaId ?? "-"}</strong></div>
        <div><span>Template</span><strong>{task?.template_id ?? selection.templateId ?? "-"}</strong></div>
      </div>

      {conversionBlocked ? (
        <div className="inline-notice inline-notice--warning">
          Resolve mapping review or the failed task state before conversion.
        </div>
      ) : null}

      <div className="detail-grid">
        <div className="detail-grid__canonical">
          <div className="subsection-heading">
            <FileJson2 aria-hidden="true" size={17} />
            <div>
              <strong>Canonical model</strong>
              <span>Fields, blocks, assets, and source provenance.</span>
            </div>
          </div>
          <CodePanel
            emptyMessage="Convert the task to generate the canonical model."
            title="canonical.json"
            value={canonical}
          />
        </div>
        <ReportTabs reports={reports} />
      </div>
    </section>
  );
}
