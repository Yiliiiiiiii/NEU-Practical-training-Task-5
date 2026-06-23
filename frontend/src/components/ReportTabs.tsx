import { GitBranch, Route, Scale, ShieldCheck } from "lucide-react";
import { useState } from "react";

import type { ReportResponse } from "../api/types";
import { CodePanel } from "./CodePanel";

export type ReportKey = "mapping" | "validation" | "consistency" | "trace";

interface ReportTabsProps {
  reports: Record<ReportKey, ReportResponse | null>;
}

const REPORT_TABS = [
  { id: "mapping" as const, label: "Mapping", icon: GitBranch },
  { id: "validation" as const, label: "Validation", icon: ShieldCheck },
  { id: "consistency" as const, label: "Consistency", icon: Scale },
  { id: "trace" as const, label: "Trace", icon: Route },
];

export function ReportTabs({ reports }: ReportTabsProps) {
  const [activeTab, setActiveTab] = useState<ReportKey>("mapping");
  const active = REPORT_TABS.find((tab) => tab.id === activeTab) ?? REPORT_TABS[0];

  return (
    <section className="report-workbench" aria-label="Task 报告">
      <div className="report-tabs" aria-label="报告类型">
        {REPORT_TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              aria-pressed={activeTab === tab.id}
              className={activeTab === tab.id ? "report-tab report-tab--active" : "report-tab"}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              <Icon aria-hidden="true" size={15} />
              {tab.label}
            </button>
          );
        })}
      </div>
      <CodePanel
        emptyMessage={`${active.label} report 尚未生成。`}
        title={`${active.label} report`}
        value={reports[active.id]}
      />
    </section>
  );
}
