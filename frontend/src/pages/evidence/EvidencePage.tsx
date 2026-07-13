import { useEffect, useState } from "react";

import { api } from "../../api";
import { ChunkEvidencePanel } from "../../components/ChunkEvidencePanel";
import { EvaluationCenterPanel } from "../../components/EvaluationCenterPanel";
import { LineagePanel } from "../../components/LineagePanel";
import { MappingEvidencePanel } from "../../components/MappingEvidencePanel";
import { PackageManifestPanel } from "../../components/PackageManifestPanel";
import { ValidationIssuePanel } from "../../components/ValidationIssuePanel";
import { PageState } from "../../components/feedback/PageState";
import type {
  ChunksReport,
  MappingReport,
  PackageManifest,
  TaskListItem,
  ValidationReport,
  VerifierReport
} from "../../types";

type TaskEvidence = {
  mapping: MappingReport | null;
  validation: ValidationReport | null;
  chunks: ChunksReport | null;
  manifest: PackageManifest | null;
  verifier: VerifierReport | null;
};

const emptyEvidence: TaskEvidence = {
  mapping: null,
  validation: null,
  chunks: null,
  manifest: null,
  verifier: null
};

const TASK_PAGE_SIZE = 100;

function settledValue<T>(result: PromiseSettledResult<T>): T | null {
  return result.status === "fulfilled" ? result.value : null;
}

export function EvidencePage() {
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [taskLoading, setTaskLoading] = useState(true);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [evidenceLoaded, setEvidenceLoaded] = useState(false);
  const [error, setError] = useState("");
  const [evidence, setEvidence] = useState<TaskEvidence>(emptyEvidence);

  useEffect(() => {
    let active = true;
    void loadTasks(() => active);
    return () => {
      active = false;
    };
  }, []);

  async function loadTasks(isActive: () => boolean) {
    setTaskLoading(true);
    setError("");
    try {
      const firstPage = await api.listTasks(1, TASK_PAGE_SIZE);
      if (!isActive()) return;
      const items = [...firstPage.items];
      for (let page = 2; items.length < firstPage.total; page += 1) {
        const nextPage = await api.listTasks(page, TASK_PAGE_SIZE);
        if (!isActive()) return;
        items.push(...nextPage.items);
        if (!nextPage.items.length) break;
      }
      if (!isActive()) return;
      setTasks(items);
      setSelectedTaskId((current) => current || items[0]?.task_id || "");
    } catch (caught) {
      if (!isActive()) return;
      setError(caught instanceof Error ? caught.message : "任务列表读取失败。");
    } finally {
      if (isActive()) setTaskLoading(false);
    }
  }

  async function loadEvidence() {
    if (!selectedTaskId) return;
    setEvidenceLoading(true);
    setError("");
    const results = await Promise.allSettled([
      api.getMappingReport(selectedTaskId),
      api.getValidationReport(selectedTaskId),
      api.getChunksReport(selectedTaskId),
      api.getManifestReport(selectedTaskId),
      api.getVerifierReport(selectedTaskId)
    ]);
    setEvidence({
      mapping: settledValue(results[0]),
      validation: settledValue(results[1]),
      chunks: settledValue(results[2]),
      manifest: settledValue(results[3]),
      verifier: settledValue(results[4])
    });
    setEvidenceLoaded(true);
    if (results.some((result) => result.status === "rejected")) {
      setError("部分任务证据暂不可用；已显示服务返回的报告。");
    }
    setEvidenceLoading(false);
  }

  return (
    <section className="route-placeholder operations-page evidence-page" aria-labelledby="evidence-title">
      <p className="page-eyebrow">证据</p>
      <h1 id="evidence-title">证据与评测</h1>
      <p className="route-placeholder-description">
        Package verification 仅验证产物包、Manifest、SHA-256 与可解析性；不证明 Schema 映射语义正确。
      </p>

      <section className="operations-boundary evidence-boundary" aria-labelledby="evidence-boundary-title">
        <h2 id="evidence-boundary-title">证据边界</h2>
        <p>
          Package verification 通过不代表字段映射已通过语义正确性验证。请结合 Validation、Review、badcase 和 Evaluation 的独立结果判断。
        </p>
      </section>

      <section className="operations-section evidence-evaluation-context" aria-labelledby="evaluation-context-title">
        <h2 id="evaluation-context-title">评测数据集与运行上下文</h2>
        <EvaluationCenterPanel />
      </section>

      <section className="operations-section evidence-task-explorer" aria-labelledby="task-evidence-title">
        <h2 id="task-evidence-title">任务证据</h2>
        {taskLoading ? <PageState kind="loading" title="正在读取任务" /> : null}
        {!taskLoading && !tasks.length && !error ? <PageState kind="empty" title="暂无可选任务" /> : null}
        {tasks.length ? (
          <div className="operations-filter-bar evidence-task-controls">
            <label>
              任务
              <select
                value={selectedTaskId}
                onChange={(event) => {
                  setSelectedTaskId(event.target.value);
                  setEvidence(emptyEvidence);
                  setEvidenceLoaded(false);
                }}
              >
                {tasks.map((task) => <option key={task.task_id} value={task.task_id}>{task.task_id}</option>)}
              </select>
            </label>
            <button type="button" onClick={() => void loadEvidence()} disabled={evidenceLoading || !selectedTaskId}>
              {evidenceLoading ? "正在加载证据" : "加载任务证据"}
            </button>
          </div>
        ) : null}
        {error ? <PageState kind="partial" title="证据读取不完整" detail={error} /> : null}
        {evidenceLoaded ? (
          <div className="evidence-task-report-grid">
            <section><h3>映射证据</h3><MappingEvidencePanel report={evidence.mapping} /></section>
            <section><h3>Validation</h3><ValidationIssuePanel report={evidence.validation} /></section>
            <section><h3>Chunk 证据</h3><ChunkEvidencePanel report={evidence.chunks} /></section>
            <section><h3>Package Manifest</h3><PackageManifestPanel manifest={evidence.manifest} verifier={evidence.verifier} /></section>
            <section><h3>Lineage</h3><LineagePanel taskId={selectedTaskId} available={evidenceLoaded} /></section>
          </div>
        ) : null}
      </section>
    </section>
  );
}
