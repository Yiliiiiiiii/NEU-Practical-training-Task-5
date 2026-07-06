import { describe, expect, it } from "vitest";

import { dimensionScorecards, metricTrend } from "./evaluationView";
import type { EvaluationRun } from "./types";

function run(
  runId: string,
  metrics: Record<string, unknown>,
  createdAt: string
): EvaluationRun {
  return {
    run_id: runId,
    created_at: createdAt,
    git_commit: "test",
    dataset_id: "dataset",
    eval_type: "mapping",
    metrics,
    passed: true,
    failed_gates: [],
    report_paths: {}
  };
}

describe("evaluation view projections", () => {
  it("keeps the latest scorecard for each schema", () => {
    const runs = [
      run("old", { schema_id: "policy_doc", mapping_recall: 0.6 }, "2026-07-01"),
      run("new", { schema_id: "policy_doc", mapping_recall: 0.8 }, "2026-07-02")
    ];

    expect(dimensionScorecards(runs, "schema_id")).toEqual([
      {
        id: "policy_doc",
        metrics: { mapping_recall: 0.8 },
        passed: true,
        runId: "new"
      }
    ]);
  });

  it("returns numeric trend points in chronological order", () => {
    const runs = [
      run("new", { mapping_recall: 0.8 }, "2026-07-02"),
      run("old", { mapping_recall: 0.6 }, "2026-07-01")
    ];

    expect(metricTrend(runs, "mapping_recall")).toEqual([
      { runId: "old", value: 0.6, passed: true },
      { runId: "new", value: 0.8, passed: true }
    ]);
  });
});
