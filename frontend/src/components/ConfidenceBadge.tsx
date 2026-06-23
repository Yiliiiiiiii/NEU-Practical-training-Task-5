interface ConfidenceBadgeProps {
  value: number;
}

function confidenceLevel(value: number): { label: string; tone: "high" | "medium" | "low" } {
  if (value >= 0.9) {
    return { label: "高", tone: "high" };
  }
  if (value >= 0.75) {
    return { label: "需审核", tone: "medium" };
  }
  return { label: "低", tone: "low" };
}

export function ConfidenceBadge({ value }: ConfidenceBadgeProps) {
  const level = confidenceLevel(value);
  return (
    <span className={`confidence-badge confidence-badge--${level.tone}`}>
      <strong>{Math.round(value * 100)}%</strong>
      <span>{level.label}</span>
    </span>
  );
}
