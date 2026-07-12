// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../api";
import { ExecutionPage } from "./ExecutionPage";

vi.mock("../../api", () => ({
  api: {
    executeTask: vi.fn()
  }
}));

afterEach(cleanup);

describe("ExecutionPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("executes once after navigation, states the lack of real-time events, and links to the terminal task", async () => {
    let resolveExecution!: (value: {
      task_id: string;
      status: string;
      report_paths: Record<string, string>;
      package_zip_path: string | null;
      review_required_count: number;
      unmapped_required_count: number;
    }) => void;
    const execution = new Promise<{
      task_id: string;
      status: string;
      report_paths: Record<string, string>;
      package_zip_path: string | null;
      review_required_count: number;
      unmapped_required_count: number;
    }>((resolve) => {
      resolveExecution = resolve;
    });
    vi.mocked(api.executeTask).mockReturnValue(execution);

    render(<ExecutionPage taskId="task-exec-1" />);

    expect(api.executeTask).toHaveBeenCalledTimes(1);
    expect(api.executeTask).toHaveBeenCalledWith("task-exec-1");
    expect(screen.getByText("服务正在同步执行，当前 API 未提供实时阶段事件。")).toBeInTheDocument();
    expect(screen.queryByText("固定执行阶段")).not.toBeInTheDocument();

    await act(async () => {
      resolveExecution({
        task_id: "task-exec-1",
        status: "completed",
        report_paths: { mapping: "reports/mapping.json" },
        package_zip_path: "packages/task-exec-1.zip",
        review_required_count: 0,
        unmapped_required_count: 0
      });
    });

    await waitFor(() => expect(screen.getByRole("link", { name: "查看任务详情" })).toHaveAttribute("href", "/tasks/task-exec-1"));
    expect(api.executeTask).toHaveBeenCalledTimes(1);
  });
});
