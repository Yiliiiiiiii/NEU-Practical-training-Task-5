import { useMemo, useState } from "react";

import type { ToastInput, ToastMessage, ViewId, WorkbenchSelection, WorkflowStage } from "./appTypes";
import { AppShell } from "./components/AppShell";
import { ImportPage } from "./pages/ImportPage";

const WORKFLOW_STAGES: WorkflowStage[] = [
  { label: "Import", detail: "UIR, schema, template", state: "ready" },
  { label: "Mapping", detail: "Candidates and review", state: "pending" },
  { label: "Convert", detail: "Canonical and outputs", state: "pending" },
  { label: "Reports", detail: "Validation and trace", state: "pending" },
  { label: "Package", detail: "Manifest and ZIP", state: "pending" },
];

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
};

export default function App() {
  const [activeView, setActiveView] = useState<ViewId>("import");
  const [refreshCount, setRefreshCount] = useState(0);
  const [selection, setSelection] = useState<WorkbenchSelection>(EMPTY_SELECTION);
  const [toastLog, setToastLog] = useState<ToastMessage[]>([]);
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

  function pushToast(toast: ToastInput) {
    setToastLog((current) => [
      ...current,
      {
        ...toast,
        id: `${Date.now()}-${current.length}`,
      },
    ]);
  }

  function renderView() {
    if (activeView === "import") {
      return <ImportPage onSelectionChange={setSelection} onToast={pushToast} />;
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
      stages={WORKFLOW_STAGES}
      toasts={toasts}
    >
      {renderView()}
    </AppShell>
  );
}
