import {
  ClipboardCheck,
  RefreshCw,
} from "lucide-react";
import type { ReactNode } from "react";

import type { ToastMessage, ViewId, WorkflowStage } from "../appTypes";
import { API_BASE_URL } from "../api/client";
import { NAV_ITEMS } from "../navItems";
import { StageRail } from "./StageRail";
import { ToastRegion } from "./ToastRegion";

interface AppShellProps {
  activeView: ViewId;
  currentTaskId: string | null;
  stages: WorkflowStage[];
  toasts: ToastMessage[];
  children: ReactNode;
  onRefresh: () => void;
  onDismissToast: (id: string) => void;
  onViewChange: (view: ViewId) => void;
}

export function AppShell({
  activeView,
  currentTaskId,
  stages,
  toasts,
  children,
  onRefresh,
  onDismissToast,
  onViewChange,
}: AppShellProps) {
  return (
    <div className="workbench-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <ClipboardCheck aria-hidden="true" size={22} strokeWidth={2.2} />
          <div>
            <span className="brand-kicker">Document Workbench</span>
            <h1>SchemaPack Agent</h1>
          </div>
        </div>
        <div className="topbar__meta">
          <span title={API_BASE_URL}>API {API_BASE_URL.replace(/^https?:\/\//, "")}</span>
          <span>{currentTaskId ? `Task ${currentTaskId}` : "No task selected"}</span>
          <button className="icon-button" onClick={onRefresh} type="button">
            <RefreshCw aria-hidden="true" size={16} />
            Refresh
          </button>
        </div>
      </header>

      <aside className="workspace-rail" aria-label="Workbench navigation">
        <nav className="nav-list">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={`nav-item ${activeView === item.id ? "nav-item--active" : ""}`}
                key={item.id}
                onClick={() => onViewChange(item.id)}
                type="button"
              >
                <Icon aria-hidden="true" size={18} />
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.description}</small>
                </span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="workspace-main">
        <section className="pipeline-card" aria-label="Workflow summary">
          <div>
            <h2>UIR -&gt; Schema -&gt; Template -&gt; Task</h2>
            <p>Run the package pipeline from one readable document surface.</p>
          </div>
          <StageRail stages={stages} />
        </section>
        {children}
      </main>

      <ToastRegion messages={toasts} onDismiss={onDismissToast} />
    </div>
  );
}
