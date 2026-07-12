// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../api";
import { TaskDetailPage } from "./TaskDetailPage";

vi.mock("../../api", () => ({
  api: {
    getTask: vi.fn(),
    getMappingReport: vi.fn(),
    getValidationReport: vi.fn(),
    getContentOrganizationReport: vi.fn(),
    getChunksReport: vi.fn(),
    getManifestReport: vi.fn(),
    getVerifierReport: vi.fn(),
    getPackage: vi.fn(),
    listAuditLogs: vi.fn(),
    packageDownloadUrl: vi.fn((taskId: string) => `/downloads/${taskId}`)
  }
}));

const task = {
  task_id: "task-1",
  status: "review_required",
  doc_id: "doc-1",
  schema_id: "notice",
  schema_version: "1.0.0",
  template_id: "notice-template",
  template_version: "1.0.0",
  input_hash: "input-sha-256",
  options: { enable_llm_fallback: true },
  report_paths: { mapping: "reports/mapping.json" },
  package_zip_path: "packages/task-1.zip"
};

function prepareReports() {
  vi.mocked(api.getTask).mockResolvedValue(task);
  vi.mocked(api.getMappingReport).mockResolvedValue({
    task_id: "task-1",
    schema_id: "notice",
    summary: {},
    mappings: [
      {
        source_candidate: "标题",
        source_path: "blocks[0].text",
        target_field: "title",
        confidence: 0.62,
        evidence: ["标题文本"],
        risk_flags: ["需复核"],
        alternatives: ["subject"],
        suggested_by: "llm",
        auto_accepted: false
      }
    ],
    unmapped: [],
    review_required_items: []
  });
  vi.mocked(api.getValidationReport).mockResolvedValue({
    task_id: "task-1",
    schema_id: "notice",
    passed: true,
    summary: {},
    issues: []
  });
  vi.mocked(api.getContentOrganizationReport).mockResolvedValue({
    task_id: "task-1",
    doc_id: "doc-1",
    chunk_count: 0,
    chunks_with_summary: 0,
    chunks_with_keywords: 0,
    chunks_with_source_links: 0,
    chunks_with_content_tags: 0,
    chunks_with_quality_tags: 0,
    warnings: [],
    summary: {}
  });
  vi.mocked(api.getChunksReport).mockResolvedValue({ items: [], total: 0 });
  vi.mocked(api.getManifestReport).mockResolvedValue({
    manifest_version: "1.0",
    package_id: "pkg-1",
    package_version: "1.0",
    task_id: "task-1",
    doc_id: "doc-1",
    created_at: "2026-07-12T00:00:00Z",
    files: [{ path: "result.json", size_bytes: 12, sha256: "artifact-sha", role: "result" }],
    generator: {}
  });
  vi.mocked(api.getVerifierReport).mockResolvedValue({ passed: true, checks: [], errors: [], warnings: [] });
  vi.mocked(api.getPackage).mockResolvedValue({
    package_id: "pkg-1",
    task_id: "task-1",
    doc_id: "doc-1",
    schema_id: "notice",
    template_id: "notice-template",
    package_version: "1.0",
    zip_path: "packages/task-1.zip",
    status: "verified",
    sha256: "package-sha",
    created_at: "2026-07-12T00:00:00Z"
  });
  vi.mocked(api.listAuditLogs).mockResolvedValue({
    total: 1,
    items: [{
      audit_id: "audit-1",
      created_at: "2026-07-12T10:00:00Z",
      action: "task.execute",
      entity_type: "task",
      entity_id: "task-1",
      method: "POST",
      path: "/api/v1/tasks/task-1/execute",
      status_code: 200,
      success: true,
      metadata: { status: "completed" }
    }]
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  prepareReports();
});

afterEach(cleanup);

describe("TaskDetailPage", () => {
  it("exposes the task tabs and status with accessible Chinese labels", async () => {
    render(<TaskDetailPage taskId="task-1" />);

    await screen.findByText("task-1");
    expect(screen.getByRole("tablist", { name: "任务详情标签" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "概览" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveAttribute("aria-labelledby", "task-tab-overview");
    expect(screen.getByRole("status", { name: "需要复核" })).toBeInTheDocument();
  });

  it("only enables the verified Package download after the verifier passes", async () => {
    render(<TaskDetailPage taskId="task-1" />);

    await screen.findByText("task-1");
    fireEvent.click(screen.getByRole("tab", { name: "Package" }));

    const link = await screen.findByRole("link", { name: "下载已验证 Package" });
    expect(link).toHaveAttribute("href", "/downloads/task-1");
  });

  it("labels LLM mapping suggestions as unaccepted even when the backend marks them auto accepted", async () => {
    vi.mocked(api.getMappingReport).mockResolvedValue({
      task_id: "task-1",
      schema_id: "notice",
      summary: {},
      mappings: [{
        source_candidate: "标题",
        source_path: "blocks[0].text",
        target_field: "title",
        suggested_by: "llm",
        auto_accepted: true
      }],
      unmapped: [],
      review_required_items: []
    });
    render(<TaskDetailPage taskId="task-1" />);

    await screen.findByText("task-1");
    fireEvent.click(screen.getByRole("tab", { name: "映射" }));

    expect(await screen.findByText("LLM 建议（未自动采纳）")).toBeInTheDocument();
  });

  it("shows an empty report state when a task result report is missing", async () => {
    vi.mocked(api.getMappingReport).mockRejectedValue(new Error("报告尚未生成"));
    render(<TaskDetailPage taskId="task-1" />);

    await screen.findByText("task-1");
    fireEvent.click(screen.getByRole("tab", { name: "映射" }));

    await waitFor(() => {
      expect(screen.getByText("映射报告尚未生成")).toBeInTheDocument();
    });
  });

  it("loads task audit logs independently and renders audit events", async () => {
    render(<TaskDetailPage taskId="task-1" />);

    await screen.findByText("task-1");
    fireEvent.click(screen.getByRole("tab", { name: "执行" }));

    expect(await screen.findByText("task.execute")).toBeInTheDocument();
    expect(api.listAuditLogs).toHaveBeenCalledWith("task-1");
  });
});
