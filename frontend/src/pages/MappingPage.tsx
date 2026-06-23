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
    throw new Error("Select or enter a task first.");
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
            title: "Schema fields unavailable",
            detail: error instanceof Error ? error.message : "Target field lookup failed.",
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
          title: "Mapping rows unavailable",
          detail: error instanceof Error ? error.message : "Generate candidates before mapping.",
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
        detail: error instanceof Error ? error.message : "Unexpected mapping failure.",
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
        setRunSummary(`${response.candidate_count} candidates generated`);
        onSelectionChange({ ...selection, taskStatus: response.status });
        onToast?.({
          tone: "success",
          title: "Candidates generated",
          detail: `${response.candidate_count} source fields found.`,
        });
      },
      "Candidate generation failed",
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
          `${response.mapped_count} mapped, ${response.review_required_count} need review`,
        );
        onSelectionChange({ ...selection, taskStatus: response.status });
        onToast?.({
          tone: response.review_required_count ? "warning" : "success",
          title: "Mapping completed",
          detail: `${response.review_required_count} rows need review.`,
        });
      },
      "Mapping failed",
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
          title: "Review saved",
          detail: `${response.updated} mapping updated.`,
        });
      },
      "Review failed",
    );
  }

  return (
    <section className="document-panel mapping-page" aria-labelledby="mapping-page-title">
      <div className="document-panel__header">
        <div>
          <span className="section-label">Field alignment</span>
          <h2 id="mapping-page-title">Mapping review</h2>
          <p>Generate source candidates, run deterministic mapping, then confirm review rows.</p>
        </div>
        <div className="button-row">
          <button
            className="secondary-button"
            disabled={isBusy || !selection.taskId}
            onClick={() => void refreshRows()}
            type="button"
          >
            <RotateCw aria-hidden="true" size={15} />
            Refresh rows
          </button>
          <button
            className="secondary-button"
            disabled={isBusy || !selection.taskId}
            onClick={() => void handleGenerateCandidates()}
            type="button"
          >
            <Wand2 aria-hidden="true" size={15} />
            Generate candidates
          </button>
          <button
            className="primary-button"
            disabled={isBusy || !selection.taskId}
            onClick={() => void handleRunMapping()}
            type="button"
          >
            <GitBranch aria-hidden="true" size={15} />
            Run mapping
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
          Use task
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
          <span>Candidates</span>
        </div>
        <div className="metric">
          <strong>{mappings.length}</strong>
          <span>Mappings</span>
        </div>
        <div className="metric">
          <strong>{mappings.filter((mapping) => mapping.need_review).length}</strong>
          <span>Need review</span>
        </div>
        <div className="metric">
          <strong>{derivedTargetFields.length}</strong>
          <span>Target fields</span>
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
