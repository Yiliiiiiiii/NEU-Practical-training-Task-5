// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { LineagePanel } from "../components/LineagePanel";
import type { LineageGraph, LineageQueryResult, LineageSummary } from "../types";

vi.mock("../api", () => ({
  api: {
    getLineage: vi.fn(),
    getLineageSummary: vi.fn(),
    getFieldLineage: vi.fn(),
    getChunkLineage: vi.fn(),
    getArtifactLineage: vi.fn()
  }
}));

const graph: LineageGraph = {
  graph_id: "lineage_task_1",
  doc_id: "doc_1",
  task_id: "task_1",
  package_id: "pkg_task_1",
  schema_id: "policy_doc",
  template_id: "policy_doc_base_v1",
  generated_at: "2026-07-06T00:00:00Z",
  lineage_version: "1.0",
  nodes: [
    {
      node_id: "lineage:uir_block:b1",
      node_type: "uir_block",
      label: "paragraph b1",
      status: "informational",
      block_id: "b1",
      metadata: { text_preview: "可信转换" },
      risk_flags: []
    },
    {
      node_id: "lineage:mapping_decision:map_title",
      node_type: "mapping_decision",
      label: "标题 → title",
      status: "review_required",
      field_name: "title",
      review_required_reason: "Fuzzy mapping requires human review.",
      metadata: { strategy: "fuzzy" },
      risk_flags: ["fuzzy_match"]
    },
    {
      node_id: "lineage:mapping_decision:map_date",
      node_type: "mapping_decision",
      label: "成文日期 → publish_date",
      status: "blocked",
      field_name: "publish_date",
      review_required_reason: "Known badcase blocks automatic acceptance.",
      metadata: { strategy: "fuzzy" },
      risk_flags: ["badcase_blocked"]
    },
    {
      node_id: "lineage:schema_field:title",
      node_type: "schema_field",
      label: "标题",
      status: "informational",
      field_name: "title",
      metadata: { type: "string" },
      risk_flags: []
    },
    {
      node_id: "lineage:canonical_field:title",
      node_type: "canonical_field",
      label: "title",
      status: "accepted",
      field_name: "title",
      metadata: {},
      risk_flags: []
    },
    {
      node_id: "lineage:chunk:chunk_1",
      node_type: "chunk",
      label: "chunk_1",
      status: "accepted",
      chunk_id: "chunk_1",
      metadata: { source_block_ids: ["b1"] },
      risk_flags: []
    },
    {
      node_id: "lineage:package_manifest_entry:content.json",
      node_type: "package_manifest_entry",
      label: "content.json",
      status: "accepted",
      artifact_path: "content.json",
      metadata: { role: "structured_json", sha256: "a".repeat(64) },
      risk_flags: []
    }
  ],
  edges: [
    {
      edge_id: "edge_1",
      source_node_id: "lineage:uir_block:b1",
      target_node_id: "lineage:mapping_decision:map_title",
      edge_type: "derived_from",
      evidence_ids: [],
      metadata: {}
    },
    {
      edge_id: "edge_2",
      source_node_id: "lineage:mapping_decision:map_title",
      target_node_id: "lineage:schema_field:title",
      edge_type: "mapped_to",
      evidence_ids: [],
      metadata: {}
    },
    {
      edge_id: "edge_3",
      source_node_id: "lineage:schema_field:title",
      target_node_id: "lineage:canonical_field:title",
      edge_type: "converted_to",
      evidence_ids: [],
      metadata: {}
    }
  ],
  evidence: [],
  summary: {},
  warnings: []
};

const summary: LineageSummary = {
  node_count: 7,
  edge_count: 3,
  field_count: 2,
  fields_traced: 2,
  field_lineage_coverage: 1,
  chunk_count: 1,
  chunks_traced: 1,
  chunk_lineage_coverage: 1,
  artifact_count: 1,
  artifacts_traced: 1,
  artifact_lineage_coverage: 1,
  review_required_count: 1,
  badcase_blocked_count: 1,
  knowledge_influenced_count: 0,
  lineage_coverage: 1,
  source_mode: "standard_uir"
};

const queryResult: LineageQueryResult = {
  root_node_id: "lineage:canonical_field:title",
  direction: "upstream",
  max_depth: 8,
  nodes: graph.nodes.slice(0, 5),
  edges: graph.edges,
  evidence: [],
  summary: { node_count: 5, edge_count: 3 }
};

function mockSuccessfulLoad() {
  vi.mocked(api.getLineage).mockResolvedValue(graph);
  vi.mocked(api.getLineageSummary).mockResolvedValue(summary);
  vi.mocked(api.getFieldLineage).mockResolvedValue(queryResult);
  vi.mocked(api.getChunkLineage).mockResolvedValue({
    ...queryResult,
    root_node_id: "lineage:chunk:chunk_1"
  });
  vi.mocked(api.getArtifactLineage).mockResolvedValue({
    ...queryResult,
    root_node_id: "lineage:package_manifest_entry:content.json"
  });
}

describe("LineagePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders_lineage_summary_cards", async () => {
    mockSuccessfulLoad();

    render(<LineagePanel taskId="task_1" available />);

    expect(await screen.findByText("字段覆盖率")).toBeInTheDocument();
    expect(screen.getAllByText("100%")).toHaveLength(4);
    expect(screen.getByText("1 个待 Review")).toBeInTheDocument();
  });

  it("renders_field_lineage_path", async () => {
    mockSuccessfulLoad();
    render(<LineagePanel taskId="task_1" available />);
    await screen.findByText("字段覆盖率");

    fireEvent.click(screen.getByRole("button", { name: "查询链路" }));

    expect(await screen.findByText("Fuzzy mapping requires human review.")).toBeInTheDocument();
    expect(api.getFieldLineage).toHaveBeenCalledWith("task_1", "title", "upstream", 8);
  });

  it("renders_review_required_status_text", async () => {
    mockSuccessfulLoad();

    render(<LineagePanel taskId="task_1" available />);

    expect(await screen.findByText("待 Review")).toBeInTheDocument();
  });

  it("renders_blocked_status_text", async () => {
    mockSuccessfulLoad();

    render(<LineagePanel taskId="task_1" available />);

    expect(await screen.findByText("已阻断")).toBeInTheDocument();
  });

  it("shows_traceability_not_semantic_correctness_warning", async () => {
    mockSuccessfulLoad();

    render(<LineagePanel taskId="task_1" available />);

    expect(
      await screen.findByText(/不等同于字段语义严格正确/)
    ).toBeInTheDocument();
  });

  it("handles_api_error_gracefully", async () => {
    vi.mocked(api.getLineage).mockRejectedValue(new Error("network unavailable"));
    vi.mocked(api.getLineageSummary).mockResolvedValue(summary);

    render(<LineagePanel taskId="task_1" available />);

    expect(await screen.findByText(/Lineage 暂时不可用/)).toBeInTheDocument();
    expect(screen.getByText(/network unavailable/)).toBeInTheDocument();
  });
});
