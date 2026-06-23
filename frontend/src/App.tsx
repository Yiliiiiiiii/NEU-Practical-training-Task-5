import { useCallback, useMemo, useState } from "react";

import type {
  StageState,
  ToastInput,
  ToastMessage,
  ViewId,
  WorkbenchSelection,
  WorkflowStage,
} from "./appTypes";
import { AppShell } from "./components/AppShell";
import { ImportPage } from "./pages/ImportPage";
import { MappingPage } from "./pages/MappingPage";
import { PackagePage } from "./pages/PackagePage";
import { TaskDetailPage } from "./pages/TaskDetailPage";
import { TasksPage } from "./pages/TasksPage";

const VIEW_COPY: Record<ViewId, { title: string; body: string }> = {
  import: {
    title: "导入与创建 Task",
    body: "加载 demo 或粘贴 JSON，准备 UIR、Target Schema 和 Mapping Template。",
  },
  tasks: {
    title: "Task 列表",
    body: "浏览转换 Task，打开需要检查的一项。",
  },
  mapping: {
    title: "Mapping 审核",
    body: "生成候选字段，执行确定性 Mapping，并确认需人工审核的行。",
  },
  detail: {
    title: "Task 详情与报告",
    body: "查看 Canonical 输出、Render 内容、Validation、Consistency、Mapping 和 Trace 报告。",
  },
  package: {
    title: "Package 下载",
    body: "生成标准 Package，并下载带 SHA-256 证据的 standard_package.zip。",
  },
};

const EMPTY_SELECTION: WorkbenchSelection = {
  docId: null,
  schemaId: null,
  templateId: null,
  taskId: null,
  taskStatus: null,
};

const CANDIDATE_DONE_STATUSES = new Set([
  "candidates_ready",
  "review_required",
  "mapping_completed",
  "rendered",
  "completed",
]);
const MAPPING_DONE_STATUSES = new Set([
  "review_required",
  "mapping_completed",
  "rendered",
  "completed",
]);
const REVIEW_DONE_STATUSES = new Set(["mapping_completed", "rendered", "completed"]);

function stageStateForCandidates(status: string | null, hasTask: boolean): StageState {
  if (status && CANDIDATE_DONE_STATUSES.has(status)) {
    return "done";
  }
  return hasTask ? "ready" : "pending";
}

function stageStateForMapping(status: string | null): StageState {
  if (status === "review_required") {
    return "done";
  }
  if (status && MAPPING_DONE_STATUSES.has(status)) {
    return "done";
  }
  if (status === "candidates_ready") {
    return "ready";
  }
  return "pending";
}

function stageStateForReview(status: string | null): StageState {
  if (status === "review_required") {
    return "blocked";
  }
  if (status && REVIEW_DONE_STATUSES.has(status)) {
    return "done";
  }
  return "pending";
}

export default function App() {
  const [activeView, setActiveView] = useState<ViewId>("import");
  const [selection, setSelection] = useState<WorkbenchSelection>(EMPTY_SELECTION);
  const [toastLog, setToastLog] = useState<ToastMessage[]>([]);
  const workflowStages = useMemo<WorkflowStage[]>(() => {
    const hasImportBundle = Boolean(selection.docId && selection.schemaId && selection.templateId);
    const candidateState = stageStateForCandidates(selection.taskStatus, Boolean(selection.taskId));
    const mappingState = stageStateForMapping(selection.taskStatus);
    const reviewState = stageStateForReview(selection.taskStatus);
    const isRendered = selection.taskStatus === "rendered" || selection.taskStatus === "completed";
    const isCompleted = selection.taskStatus === "completed";
    const transformState = isRendered
      ? "done"
      : selection.taskStatus === "mapping_completed"
        ? "ready"
        : "pending";
    return [
      {
        label: "导入 UIR",
        detail: "文档、Schema、Template",
        state: hasImportBundle ? "done" : "ready",
      },
      { label: "生成候选字段", detail: "源字段", state: candidateState },
      { label: "字段 Mapping", detail: "Schema 对齐", state: mappingState },
      { label: "人工确认", detail: "低置信度行", state: reviewState },
      { label: "Transform", detail: "Canonical model", state: transformState },
      { label: "Render", detail: "JSON、Markdown、chunks", state: isRendered ? "done" : "pending" },
      {
        label: "Validate",
        detail: "报告与 Trace",
        state: isCompleted ? "done" : isRendered ? "ready" : "pending",
      },
      {
        label: "Package",
        detail: "Manifest 与 ZIP",
        state: isCompleted ? "done" : isRendered ? "ready" : "pending",
      },
    ];
  }, [selection.docId, selection.schemaId, selection.taskId, selection.taskStatus, selection.templateId]);
  const toasts = toastLog;
  const copy = VIEW_COPY[activeView];

  const pushToast = useCallback((toast: ToastInput) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setToastLog((current) => [...current, { ...toast, id }].slice(-3));
    window.setTimeout(() => {
      setToastLog((current) => current.filter((message) => message.id !== id));
    }, 6000);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToastLog((current) => current.filter((message) => message.id !== id));
  }, []);

  const updateSelection = useCallback((nextSelection: WorkbenchSelection) => {
    setSelection(nextSelection);
  }, []);

  function renderView() {
    if (activeView === "import") {
      return <ImportPage onSelectionChange={updateSelection} onToast={pushToast} />;
    }

    if (activeView === "tasks") {
      return (
        <TasksPage
          onSelectTask={(nextSelection) => {
            updateSelection(nextSelection);
            setActiveView("mapping");
          }}
          onToast={pushToast}
          selectedTaskId={selection.taskId}
        />
      );
    }

    if (activeView === "mapping") {
      return (
        <MappingPage
          onSelectionChange={updateSelection}
          onToast={pushToast}
          selection={selection}
        />
      );
    }

    if (activeView === "detail") {
      return (
        <TaskDetailPage
          onSelectionChange={updateSelection}
          onToast={pushToast}
          selection={selection}
        />
      );
    }

    if (activeView === "package") {
      return (
        <PackagePage
          onSelectionChange={updateSelection}
          onToast={pushToast}
          selection={selection}
        />
      );
    }

    return (
      <section className="document-panel" aria-labelledby="view-title">
        <div className="document-panel__header">
          <div>
            <span className="section-label">Phase 8</span>
            <h2 id="view-title">{copy.title}</h2>
          </div>
          <span className="doc-chip">真实 API workflow</span>
        </div>
        <p>{copy.body}</p>
        <div className="empty-state">
          <strong>工作台界面已就绪。</strong>
          <span>功能面板会按 Task 流程逐步填充这里。</span>
        </div>
      </section>
    );
  }

  return (
    <AppShell
      activeView={activeView}
      currentTaskId={selection.taskId}
      onDismissToast={dismissToast}
      onRefresh={() =>
        pushToast({
          tone: "info",
          title: "工作台已就绪",
          detail: "使用当前页面的刷新操作重新加载 API 数据。",
        })
      }
      onViewChange={setActiveView}
      stages={workflowStages}
      toasts={toasts}
    >
      {renderView()}
    </AppShell>
  );
}
