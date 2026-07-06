import type { EvaluationRun } from "./types";

export type DimensionScorecard = {
  id: string;
  metrics: Record<string, number | boolean>;
  passed: boolean;
  runId: string;
};

export function dimensionScorecards(
  runs: EvaluationRun[],
  dimension: "schema_id" | "adapter_id"
): DimensionScorecard[] {
  const latest = new Map<string, DimensionScorecard>();
  const ordered = [...runs].sort((left, right) =>
    left.created_at.localeCompare(right.created_at)
  );
  for (const run of ordered) {
    const id = run.metrics[dimension];
    if (typeof id !== "string" || !id) {
      continue;
    }
    const metrics = Object.fromEntries(
      Object.entries(run.metrics).filter(
        ([key, value]) =>
          key !== dimension && (typeof value === "number" || typeof value === "boolean")
      )
    );
    latest.set(id, {
      id,
      metrics,
      passed: run.passed,
      runId: run.run_id
    });
  }
  return [...latest.values()].sort((left, right) => left.id.localeCompare(right.id));
}

export function metricTrend(runs: EvaluationRun[], metricId: string) {
  return [...runs]
    .sort((left, right) => left.created_at.localeCompare(right.created_at))
    .flatMap((run) => {
      const value = run.metrics[metricId];
      return typeof value === "number"
        ? [{ runId: run.run_id, value, passed: run.passed }]
        : [];
    })
    .slice(-8);
}
