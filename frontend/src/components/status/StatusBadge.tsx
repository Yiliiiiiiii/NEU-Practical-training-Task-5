import { formatStatus } from "../../app/format";

export type StatusBadgeProps = {
  status: string;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const label = formatStatus(status);

  return (
    <span className={`status-badge status-${status.toLowerCase()}`} role="status">
      {label}
    </span>
  );
}
