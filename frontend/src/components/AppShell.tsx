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
            <span className="brand-kicker">数据治理工作台</span>
            <h1>SchemaPack Agent</h1>
            <small>数据格式标准化转换智能体</small>
          </div>
        </div>
        <div className="topbar__meta">
          <span className="topbar-pill">Phase 10</span>
          <span title={API_BASE_URL}>API {API_BASE_URL.replace(/^https?:\/\//, "")}</span>
          <span>{currentTaskId ? `Task ${currentTaskId}` : "未选择 Task"}</span>
          <button className="icon-button" onClick={onRefresh} type="button">
            <RefreshCw aria-hidden="true" size={16} />
            刷新
          </button>
        </div>
      </header>

      <aside className="workspace-rail" aria-label="工作台导航">
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
        <div className="rail-status">
          <strong>SchemaPack Agent</strong>
          <span>运行中</span>
        </div>
      </aside>

      <main className="workspace-main">
        <section className="pipeline-card" aria-label="Workflow 概览">
          <div>
            <h2>UIR -&gt; Schema -&gt; Mapping -&gt; Transform</h2>
            <p>Canonical -&gt; Render -&gt; Validate -&gt; Manifest -&gt; ZIP</p>
          </div>
          <StageRail stages={stages} />
        </section>
        {children}
      </main>

      <ToastRegion messages={toasts} onDismiss={onDismissToast} />
    </div>
  );
}
