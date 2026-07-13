// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { StrictMode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../api";
import { EvidencePage } from "./EvidencePage";

vi.mock("../../api", () => ({
  api: {
    listTasks: vi.fn(),
    getMappingReport: vi.fn(),
    getValidationReport: vi.fn(),
    getChunksReport: vi.fn(),
    getManifestReport: vi.fn(),
    getVerifierReport: vi.fn()
  }
}));

vi.mock("../../components/EvaluationCenterPanel", () => ({
  EvaluationCenterPanel: () => <div>评测上下文</div>
}));
vi.mock("../../components/ChunkEvidencePanel", () => ({
  ChunkEvidencePanel: () => <div />
}));
vi.mock("../../components/LineagePanel", () => ({
  LineagePanel: () => <div />
}));
vi.mock("../../components/MappingEvidencePanel", () => ({
  MappingEvidencePanel: ({ report }: { report: { task_id: string } | null }) => (
    <div data-testid="mapping-report">{report?.task_id ?? "empty"}</div>
  )
}));
vi.mock("../../components/PackageManifestPanel", () => ({
  PackageManifestPanel: () => <div />
}));
vi.mock("../../components/ValidationIssuePanel", () => ({
  ValidationIssuePanel: () => <div />
}));

function task(index: number) {
  return {
    task_id: `task-${index}`,
    doc_id: `doc-${index}`,
    schema_id: "notice",
    template_id: "notice-v1",
    status: "created"
  };
}

function deferred<T>() {
  let resolve: (value: T) => void = () => undefined;
  let reject: (reason?: unknown) => void = () => undefined;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe("EvidencePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(cleanup);

  it("loads every task page so selectors include tasks beyond the first 100", async () => {
    vi.mocked(api.listTasks)
      .mockResolvedValueOnce({
        items: Array.from({ length: 100 }, (_, index) => task(index + 1)),
        total: 101
      })
      .mockResolvedValueOnce({ items: [task(101)], total: 101 });

    render(<EvidencePage />);

    expect(await screen.findByRole("option", { name: "task-101" })).toBeInTheDocument();
    expect(api.listTasks).toHaveBeenNthCalledWith(1, 1, 100);
    expect(api.listTasks).toHaveBeenNthCalledWith(2, 2, 100);
    await waitFor(() => expect(screen.getAllByRole("option")).toHaveLength(101));
  });

  it("ignores a stale task-list failure after a newer StrictMode load succeeds", async () => {
    let rejectFirstLoad: (reason?: unknown) => void = () => undefined;
    vi.mocked(api.listTasks)
      .mockReturnValueOnce(new Promise((_, reject) => {
        rejectFirstLoad = reject;
      }))
      .mockResolvedValueOnce({ items: [task(2)], total: 1 });

    render(<StrictMode><EvidencePage /></StrictMode>);

    expect(await screen.findByRole("option", { name: "task-2" })).toBeInTheDocument();
    rejectFirstLoad(new Error("stale task-list failure"));

    await waitFor(() => expect(screen.getByRole("option", { name: "task-2" })).toBeInTheDocument());
    expect(screen.queryByText("stale task-list failure")).not.toBeInTheDocument();
  });

  it("keeps a newly selected task clear when an older evidence request settles", async () => {
    const mapping = deferred<Awaited<ReturnType<typeof api.getMappingReport>>>();
    const validation = deferred<Awaited<ReturnType<typeof api.getValidationReport>>>();
    const chunks = deferred<Awaited<ReturnType<typeof api.getChunksReport>>>();
    const manifest = deferred<Awaited<ReturnType<typeof api.getManifestReport>>>();
    const verifier = deferred<Awaited<ReturnType<typeof api.getVerifierReport>>>();

    vi.mocked(api.listTasks).mockResolvedValue({ items: [task(1), task(2)], total: 2 });
    vi.mocked(api.getMappingReport).mockReturnValue(mapping.promise);
    vi.mocked(api.getValidationReport).mockReturnValue(validation.promise);
    vi.mocked(api.getChunksReport).mockReturnValue(chunks.promise);
    vi.mocked(api.getManifestReport).mockReturnValue(manifest.promise);
    vi.mocked(api.getVerifierReport).mockReturnValue(verifier.promise);

    render(<EvidencePage />);

    const selector = await screen.findByRole("combobox");
    const loadButton = screen.getByRole("button");
    fireEvent.click(loadButton);
    await waitFor(() => expect(api.getVerifierReport).toHaveBeenCalledWith("task-1"));

    fireEvent.change(selector, { target: { value: "task-2" } });
    expect(loadButton).toBeEnabled();

    await act(async () => {
      mapping.resolve({
        task_id: "task-1",
        schema_id: "notice",
        summary: {},
        mappings: [],
        unmapped: [],
        review_required_items: []
      });
      validation.reject(new Error("task-1 validation unavailable"));
      chunks.resolve({ items: [], total: 0 });
      manifest.resolve({
        manifest_version: "1.0",
        package_id: "package-1",
        package_version: "1.0",
        task_id: "task-1",
        doc_id: "doc-1",
        created_at: "2026-07-12T00:00:00Z",
        files: [],
        generator: {}
      });
      verifier.resolve({ passed: true, checks: [], errors: [], warnings: [] });
      await Promise.allSettled([
        mapping.promise,
        validation.promise,
        chunks.promise,
        manifest.promise,
        verifier.promise
      ]);
    });

    expect(selector).toHaveValue("task-2");
    expect(loadButton).toBeEnabled();
    expect(screen.queryByTestId("mapping-report")).not.toBeInTheDocument();
    expect(screen.queryByText(/部分任务证据暂不可用/)).not.toBeInTheDocument();
  });
});
