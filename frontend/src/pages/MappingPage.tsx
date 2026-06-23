import { GitBranch, ListChecks, RotateCw, Wand2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import type { CandidateListItem, JsonValue, MappingListItem } from "../api/types";
import type { ToastInput, WorkbenchSelection } from "../appTypes";
import { MappingTable } from "../components/MappingTable";

interface MappingPageProps {
  selection: WorkbenchSelection;
  onSelectionChange: (selection: WorkbenchSelection) => void;
  onToast?: (toast: ToastInput) => void;
}

function requireTaskId(taskId: string | null): string {
  if (!taskId) {
    throw new Error("请先选择或输入 Task。");
  }
  return taskId;
}

function formatSample(value: JsonValue | null): string {
  if (value === null) {
    return "-";
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value);
}

export function MappingPage({ selection, onSelectionChange, onToast }: MappingPageProps) {
  const [taskIdInput, setTaskIdInput] = useState(selection.taskId ?? "");
  const [candidates, setCandidates] = useState<CandidateListItem[]>([]);
  const [mappings, setMappings] = useState<MappingListItem[]>([]);
  const [targetFields, setTargetFields] = useState<string[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [runSummary, setRunSummary] = useState<string | null>(null);
  const [enableLlmFallback, setEnableLlmFallback] = useState(true);

  useEffect(() => {
    setTaskIdInput(selection.taskId ?? "");
  }, [selection.taskId]);

  useEffect(() => {
    if (!selection.schemaId) {
      setTargetFields([]);
      return;
    }

    let isActive = true;
    void api
      .getSchema(selection.schemaId)
      .then((schema) => {
        if (isActive) {
          setTargetFields(schema.fields.map((field) => field.field_id));
        }
      })
      .catch((error) => {
        if (isActive) {
          setTargetFields([]);
          onToast?.({
            tone: "warning",
            title: "Schema 字段不可用",
            detail: error instanceof Error ? error.message : "Target field 查询失败。",
          });
        }
      });
    return () => {
      isActive = false;
    };
  }, [onToast, selection.schemaId]);

  const derivedTargetFields = useMemo(
    () =>
      targetFields.length
        ? targetFields
        : Array.from(new Set(mappings.map((mapping) => mapping.target_field_id))),
    [mappings, targetFields],
  );
  const candidateSamples = useMemo(
    () =>
      Object.fromEntries(
        candidates.map((candidate) => [
          candidate.candidate_id,
          formatSample(candidate.value_sample),
        ]),
      ),
    [candidates],
  );

  function useManualTaskId() {
    const taskId = taskIdInput.trim();
    if (!taskId) {
      return;
    }
    onSelectionChange({
      ...selection,
      taskId,
      taskStatus: selection.taskStatus ?? "created",
    });
  }

  const refreshRows = useCallback(
    async (taskId = selection.taskId) => {
      try {
        const currentTaskId = requireTaskId(taskId);
        const [candidateResponse, mappingResponse] = await Promise.all([
          api.listCandidates(currentTaskId),
          api.listMappings(currentTaskId),
        ]);
        setCandidates(candidateResponse.items);
        setMappings(mappingResponse.items);
      } catch (error) {
        onToast?.({
          tone: "warning",
          title: "Mapping 行不可用",
          detail: error instanceof Error ? error.message : "请先生成候选字段再执行 Mapping。",
        });
      }
    },
    [onToast, selection.taskId],
  );

  useEffect(() => {
    if (!selection.taskId) {
      setCandidates([]);
      setMappings([]);
      return;
    }
    void refreshRows(selection.taskId);
  }, [refreshRows, selection.taskId]);

  async function runAction(action: () => Promise<void>, failureTitle: string) {
    setIsBusy(true);
    try {
      await action();
    } catch (error) {
      onToast?.({
        tone: "danger",
        title: failureTitle,
        detail: error instanceof Error ? error.message : "Mapping 过程中发生未知错误。",
      });
    } finally {
      setIsBusy(false);
    }
  }

  async function handleGenerateCandidates() {
    await runAction(
      async () => {
        const taskId = requireTaskId(selection.taskId);
        const response = await api.generateCandidates(taskId);
        const candidateResponse = await api.listCandidates(taskId);
        setCandidates(candidateResponse.items);
        setRunSummary(`${response.candidate_count} 个候选字段已生成`);
        onSelectionChange({ ...selection, taskStatus: response.status });
        onToast?.({
          tone: "success",
          title: "候选字段已生成",
          detail: `找到 ${response.candidate_count} 个源字段。`,
        });
      },
      "候选字段生成失败",
    );
  }

  async function handleRunMapping() {
    await runAction(
      async () => {
        const taskId = requireTaskId(selection.taskId);
        const response = await api.runMapping(taskId, 0.8, enableLlmFallback);
        const mappingResponse = await api.listMappings(taskId);
        setMappings(mappingResponse.items);
        setRunSummary(
          `${response.mapped_count} 个已 Mapping，${response.review_required_count} 个需审核`,
        );
        onSelectionChange({ ...selection, taskStatus: response.status });
        onToast?.({
          tone: response.review_required_count ? "warning" : "success",
          title: "Mapping 已完成",
          detail: `${response.review_required_count} 行需审核。`,
        });
      },
      "Mapping 失败",
    );
  }

  async function handleReview(mapping: MappingListItem, targetFieldId: string) {
    await runAction(
      async () => {
        const taskId = requireTaskId(selection.taskId);
        const response = await api.reviewMappings(taskId, [
          {
            mapping_id: mapping.mapping_id,
            new_target_field_id: targetFieldId,
            decision: "confirmed",
            reviewer: "human",
          },
        ]);
        await refreshRows(taskId);
        onToast?.({
          tone: "success",
          title: "审核已保存",
          detail: `${response.updated} 条 Mapping 已更新。`,
        });
      },
      "审核保存失败",
    );
  }

  return (
    <section className="document-panel mapping-page" aria-labelledby="mapping-page-title">
      <div className="document-panel__header">
        <div>
          <span className="section-label">字段对齐</span>
          <h2 id="mapping-page-title">Mapping 审核</h2>
          <p>生成源字段候选，执行确定性 Mapping，然后确认需审核的行。</p>
        </div>
        <div className="button-row">
          <button
            className="secondary-button"
            disabled={isBusy || !selection.taskId}
            onClick={() => void refreshRows()}
            type="button"
          >
            <RotateCw aria-hidden="true" size={15} />
            刷新行
          </button>
          <button
            className="secondary-button"
            disabled={isBusy || !selection.taskId}
            onClick={() => void handleGenerateCandidates()}
            type="button"
          >
            <Wand2 aria-hidden="true" size={15} />
            生成候选字段
          </button>
          <button
            className="primary-button"
            disabled={isBusy || !selection.taskId}
            onClick={() => void handleRunMapping()}
            type="button"
          >
            <GitBranch aria-hidden="true" size={15} />
            执行 Mapping
          </button>
        </div>
      </div>

      <div className="task-picker">
        <label>
          Task ID
          <input
            onChange={(event) => setTaskIdInput(event.target.value)}
            placeholder="task_id"
            type="text"
            value={taskIdInput}
          />
        </label>
        <button className="secondary-button" onClick={useManualTaskId} type="button">
          <ListChecks aria-hidden="true" size={15} />
          使用 Task
        </button>
        <label className="fallback-toggle">
          <input
            checked={enableLlmFallback}
            disabled={isBusy}
            onChange={(event) => setEnableLlmFallback(event.target.checked)}
            type="checkbox"
          />
          <span>DeepSeek fallback</span>
        </label>
        {runSummary ? <span>{runSummary}</span> : null}
      </div>

      <div className="metric-row">
        <div className="metric">
          <strong>{candidates.length}</strong>
          <span>候选字段</span>
        </div>
        <div className="metric">
          <strong>{mappings.length}</strong>
          <span>Mappings</span>
        </div>
        <div className="metric">
          <strong>{mappings.filter((mapping) => mapping.need_review).length}</strong>
          <span>需审核</span>
        </div>
        <div className="metric">
          <strong>{derivedTargetFields.length}</strong>
          <span>目标字段</span>
        </div>
      </div>

      <MappingTable
        candidateSamples={candidateSamples}
        mappings={mappings}
        onReview={handleReview}
        targetFields={derivedTargetFields}
      />
    </section>
  );
}
