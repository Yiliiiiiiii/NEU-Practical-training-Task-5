// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { EvaluationCenterPanel } from "../components/EvaluationCenterPanel";
import type { EvaluationScorecard } from "../types";

vi.mock("../api", () => ({
  api: {
    listEvaluationDatasets: vi.fn(),
    listEvaluationMetrics: vi.fn(),
    listEvaluationRuns: vi.fn(),
    getEvaluationScorecard: vi.fn(),
    evaluationReportUrl: vi.fn(() => "#")
  }
}));

const scorecard = {
  run_count: 1,
  metrics: {
    package_verification_rate: 1,
    strict_validation_rate: 17 / 35,
    badcase_violation_count: 0,
    llm_auto_accepted_count: 0
  },
  passed: true,
  failed_gates: [],
  summary: {
    status: "passed" as const,
    generated_at: "2026-07-05T00:00:00Z",
    gates_passed: 4,
    gates_total: 4
  },
  cards: [
    {
      metric_id: "package_verification_rate",
      name: "Package Verification",
      value: 1,
      target: 1,
      status: "passed" as const,
      explanation: "Package structure and traceability are valid."
    },
    {
      metric_id: "strict_validation_rate",
      name: "Strict Validation",
      value: 17 / 35,
      target: 0.7,
      status: "needs_attention" as const,
      explanation: "Semantic validation remains separate."
    },
    {
      metric_id: "router_top1_accuracy",
      name: "Router Accuracy",
      value: 0.5,
      target: 0.85,
      status: "failed" as const,
      explanation: "Expanded fixture accuracy."
    }
  ],
  warnings: [
    "Package verification does not imply every target field passes strict semantic validation.",
    "LLM suggestions and Schema Drafts never activate production rules automatically."
  ]
};

function mockSuccessfulLoad(overrides: Partial<EvaluationScorecard> = {}) {
  vi.mocked(api.listEvaluationDatasets).mockResolvedValue({
    items: [
      {
        dataset_id: "external_uir_adapter_v1",
        dataset_type: "external_uir",
        doc_count: 18,
        doc_types: { meeting_doc: 4 },
        gold_files: ["examples/external_uir/expected"]
      }
    ]
  });
  vi.mocked(api.listEvaluationMetrics).mockResolvedValue({ items: [] });
  vi.mocked(api.listEvaluationRuns).mockResolvedValue({
    items: [
      {
        run_id: "run-1",
        created_at: "2026-07-05T00:00:00Z",
        git_commit: "test",
        dataset_id: "external_uir_adapter_v1",
        eval_type: "adapter",
        metrics: { package_verification_rate: 1 },
        passed: true,
        failed_gates: [],
        report_paths: { json: "reports/adapter.json" }
      }
    ],
    total: 1
  });
  vi.mocked(api.getEvaluationScorecard).mockResolvedValue({
    ...scorecard,
    ...overrides
  });
}

describe("EvaluationCenterPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders four sections, scorecard states and semantic warning", async () => {
    mockSuccessfulLoad();

    render(<EvaluationCenterPanel />);

    expect(await screen.findByText("数据集目录")).toBeInTheDocument();
    expect(screen.getByText("评测运行")).toBeInTheDocument();
    expect(screen.getByText("指标记分卡")).toBeInTheDocument();
    expect(screen.getByText("回归门")).toBeInTheDocument();
    expect(screen.getAllByText("通过").length).toBeGreaterThan(0);
    expect(screen.getByText("需关注")).toBeInTheDocument();
    expect(screen.getByText("失败")).toBeInTheDocument();
    expect(
      screen.getByText(/Package verification 证明成果包结构/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/不代表所有 target field 都通过 strict semantic validation/)
    ).toBeInTheDocument();
  });

  it("shows a useful fallback when the API fails", async () => {
    vi.mocked(api.listEvaluationDatasets).mockRejectedValue(
      new Error("network unavailable")
    );
    vi.mocked(api.listEvaluationMetrics).mockResolvedValue({ items: [] });
    vi.mocked(api.listEvaluationRuns).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(api.getEvaluationScorecard).mockResolvedValue(scorecard);

    render(<EvaluationCenterPanel />);

    expect(
      await screen.findByText(/评测数据暂时不可用/)
    ).toBeInTheDocument();
    expect(screen.getByText(/network unavailable/)).toBeInTheDocument();
  });

  it("forces failed labels for unsafe badcase and LLM values", async () => {
    mockSuccessfulLoad({
      metrics: {
        ...scorecard.metrics,
        badcase_violation_count: 2,
        llm_auto_accepted_count: 1
      },
      cards: [
        {
          metric_id: "badcase_violation_count",
          name: "Badcase Safety",
          value: 2,
          target: 0,
          status: "passed" as const,
          explanation: "Must remain zero."
        },
        {
          metric_id: "llm_auto_accepted_count",
          name: "LLM Auto Accept",
          value: 1,
          target: 0,
          status: "passed" as const,
          explanation: "Must remain zero."
        }
      ]
    });

    render(<EvaluationCenterPanel />);

    expect(await screen.findByText("Badcase Safety")).toBeInTheDocument();
    expect(screen.getByText("LLM Auto Accept")).toBeInTheDocument();
    expect(
      screen
        .getAllByText("失败")
        .filter((label) => label.closest(".evaluation-card"))
    ).toHaveLength(2);
  });
});
