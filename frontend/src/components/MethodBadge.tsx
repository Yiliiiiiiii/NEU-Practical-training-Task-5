interface MethodBadgeProps {
  method: string;
}

function normalizeMethod(method: string): string {
  const normalized = method.toLowerCase();
  if (normalized.includes("exact")) {
    return "exact";
  }
  if (normalized.includes("alias")) {
    return "alias";
  }
  if (normalized.includes("regex")) {
    return "regex";
  }
  if (normalized.includes("type")) {
    return "type";
  }
  if (normalized.includes("fuzzy")) {
    return "fuzzy";
  }
  if (normalized.includes("llm")) {
    return "llm";
  }
  if (normalized.includes("manual")) {
    return "manual";
  }
  return normalized.replace(/_match|_fallback/g, "") || "manual";
}

export function MethodBadge({ method }: MethodBadgeProps) {
  const label = normalizeMethod(method);
  return <span className={`method-badge method-badge--${label}`}>{label}</span>;
}
