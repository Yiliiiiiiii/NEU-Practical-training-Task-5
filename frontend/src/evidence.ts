import type {
  ChunkPreview,
  ManifestFile,
  PackageManifest,
  ValidationIssue,
  VerifierReport
} from "./types";

export type ChunkFilter = {
  strategy: string;
  tablesOnly: boolean;
  flaggedOnly: boolean;
};

export function filterChunks<T extends Partial<ChunkPreview>>(
  chunks: T[],
  filter: ChunkFilter
): T[] {
  return chunks.filter((chunk) => {
    const strategyOk =
      filter.strategy === "all" || chunk.strategy === filter.strategy;
    const tags = [...(chunk.content_tags ?? []), ...(chunk.tags?.content ?? [])];
    const quality = [...(chunk.quality_flags ?? []), ...(chunk.quality_tags ?? [])];
    const tableOk = !filter.tablesOnly || tags.includes("table");
    const flaggedOk = !filter.flaggedOnly || quality.length > 0;
    return strategyOk && tableOk && flaggedOk;
  });
}

export function suggestedAction(issue: Partial<ValidationIssue>): string {
  const severity = String(issue.severity ?? issue.level ?? "").toLowerCase();
  const message = String(issue.message ?? "").toLowerCase();
  if (severity === "error" || message.includes("missing")) {
    return "Review the source evidence and complete or reject this field.";
  }
  if (message.includes("format") || message.includes("type")) {
    return "Check the transform rule and normalize the source value.";
  }
  return "Keep the evidence attached and monitor in the next verification run.";
}

export function truncateSha(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  return value.length <= 24 ? value : `${value.slice(0, 12)}…${value.slice(-7)}`;
}

export function mappingTone(item: Record<string, unknown>): "good" | "warn" | "bad" {
  const status = String(item.status ?? "").toLowerCase();
  const confidenceTier = String(item.confidence_tier ?? "").toLowerCase();
  const riskFlags = Array.isArray(item.risk_flags) ? item.risk_flags : [];
  if (status.includes("accepted") && confidenceTier !== "low" && !riskFlags.length) {
    return "good";
  }
  if (status.includes("failed") || riskFlags.includes("badcase_blocked")) {
    return "bad";
  }
  return "warn";
}

export function mergeManifestVerification(
  manifest: PackageManifest | null,
  verifier: VerifierReport | null
): Array<ManifestFile & { verified: boolean; verifier_message?: string }> {
  const errors = new Set((verifier?.errors ?? []).map((item) => String(item)));
  return (manifest?.files ?? []).map((file) => ({
    ...file,
    verified: Boolean(verifier?.passed) && !errors.has(file.path),
    verifier_message: errors.has(file.path) ? "Verifier reported this path." : undefined
  }));
}
