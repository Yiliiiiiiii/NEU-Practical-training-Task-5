import type { StageState } from "../appTypes";

interface StatusBadgeProps {
  status: StageState | string;
  label?: string;
}

const KNOWN_STATUS: Record<string, StageState> = {
  created: "pending",
  candidates_ready: "ready",
  mapping_completed: "ready",
  review_required: "blocked",
  transforming: "running",
  rendered: "ready",
  completed: "done",
  failed: "blocked",
};

const STATUS_LABELS: Record<string, string> = {
  blocked: "受阻",
  cancelled: "已取消",
  candidates_ready: "候选已生成",
  completed: "已完成",
  confirmed: "已确认",
  created: "已创建",
  done: "完成",
  failed: "失败",
  mapping_completed: "Mapping 已完成",
  pending: "待处理",
  ready: "就绪",
  rendered: "已 Render",
  review_required: "需人工确认",
  running: "运行中",
  transforming: "Transform 中",
};

function normalizeStatus(status: string): StageState {
  return KNOWN_STATUS[status] ?? "pending";
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const normalized = normalizeStatus(status);
  const rawStatus = String(status).replace(/[^a-z0-9_-]/gi, "_").toLowerCase();

  return (
    <span className={`status-badge status-badge--${normalized} status-badge--${rawStatus}`}>
      <span aria-hidden="true" className="status-badge__dot" />
      {label ?? STATUS_LABELS[status] ?? status}
    </span>
  );
}
