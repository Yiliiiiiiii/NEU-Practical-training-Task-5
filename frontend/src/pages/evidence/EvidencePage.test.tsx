// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { StrictMode } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../api";
import { EvidencePage } from "./EvidencePage";

vi.mock("../../api", () => ({
  api: {
    listTasks: vi.fn()
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
  MappingEvidencePanel: () => <div />
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
});
