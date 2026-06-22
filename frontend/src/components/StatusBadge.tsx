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

function normalizeStatus(status: string): StageState {
  return KNOWN_STATUS[status] ?? "pending";
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const normalized = normalizeStatus(status);

  return (
    <span className={`status-badge status-badge--${normalized}`}>
      <span aria-hidden="true" className="status-badge__dot" />
      {label ?? status}
    </span>
  );
}
