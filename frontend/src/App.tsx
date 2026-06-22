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
    title: "Import and setup",
    body: "Load demo or pasted JSON for the UIR document, Target Schema, and Mapping Template.",
  },
  tasks: {
    title: "Tasks",
    body: "Browse conversion tasks and open the one you want to inspect.",
  },
  mapping: {
    title: "Mapping review",
    body: "Generate candidates, run deterministic mapping, and confirm review-required rows.",
  },
  detail: {
    title: "Task detail and reports",
    body: "Read canonical output, rendered content, validation, consistency, mapping, and trace reports.",
  },
  package: {
    title: "Package download",
    body: "Generate the standard package and download standard_package.zip with SHA-256 evidence.",
  },
};

const EMPTY_SELECTION: WorkbenchSelection = {
  docId: null,
  schemaId: null,
  templateId: null,
  taskId: null,
  taskStatus: null,
};

const MAPPED_STATUSES = new Set(["mapping_completed", "rendered", "completed"]);

function stageStateForMapping(status: string | null, hasTask: boolean): StageState {
  if (status === "review_required") {
    return "blocked";
  }
  if (status && MAPPED_STATUSES.has(status)) {
    return "done";
  }
  if (status === "candidates_ready" || hasTask) {
    return "ready";
  }
  return "pending";
}

export default function App() {
  const [activeView, setActiveView] = useState<ViewId>("import");
  const [refreshCount, setRefreshCount] = useState(0);
  const [selection, setSelection] = useState<WorkbenchSelection>(EMPTY_SELECTION);
  const [toastLog, setToastLog] = useState<ToastMessage[]>([]);
  const workflowStages = useMemo<WorkflowStage[]>(() => {
    const hasImportBundle = Boolean(selection.docId && selection.schemaId && selection.templateId);
    const mappingState = stageStateForMapping(selection.taskStatus, Boolean(selection.taskId));
    const isRendered = selection.taskStatus === "rendered" || selection.taskStatus === "completed";
    const isCompleted = selection.taskStatus === "completed";
    const convertState = isRendered
      ? "done"
      : mappingState === "done" || selection.taskStatus === "review_required"
        ? "ready"
        : "pending";
    return [
      {
        label: "Import",
        detail: "UIR, schema, template",
        state: hasImportBundle ? "done" : "ready",
      },
      { label: "Mapping", detail: "Candidates and review", state: mappingState },
      { label: "Convert", detail: "Canonical and outputs", state: convertState },
      {
        label: "Reports",
        detail: "Validation and trace",
        state: isCompleted ? "done" : isRendered ? "ready" : "pending",
      },
      {
        label: "Package",
        detail: "Manifest and ZIP",
        state: isCompleted ? "done" : isRendered ? "ready" : "pending",
      },
    ];
  }, [selection.docId, selection.schemaId, selection.taskId, selection.taskStatus, selection.templateId]);
  const toasts = useMemo<ToastMessage[]>(
    () =>
      [
        ...toastLog,
        ...(refreshCount
          ? [
              {
                id: "refresh",
                tone: "info" as const,
                title: "Workbench refreshed",
                detail: "Current view state is still local.",
              },
            ]
          : []),
      ].slice(-3),
    [refreshCount, toastLog],
  );
  const copy = VIEW_COPY[activeView];

  const pushToast = useCallback((toast: ToastInput) => {
    setToastLog((current) => [
      ...current,
      {
        ...toast,
        id: `${Date.now()}-${current.length}`,
      },
    ]);
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
          <span className="doc-chip">Real API workflow</span>
        </div>
        <p>{copy.body}</p>
        <div className="empty-state">
          <strong>Workbench surface ready.</strong>
          <span>Functional panels will fill this space task by task.</span>
        </div>
      </section>
    );
  }

  return (
    <AppShell
      activeView={activeView}
      currentTaskId={selection.taskId}
      onRefresh={() => setRefreshCount((count) => count + 1)}
      onViewChange={setActiveView}
      stages={workflowStages}
      toasts={toasts}
    >
      {renderView()}
    </AppShell>
  );
}
