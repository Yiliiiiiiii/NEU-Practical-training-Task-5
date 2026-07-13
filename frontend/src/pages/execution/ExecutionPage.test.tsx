// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../api";
import { ExecutionPage } from "./ExecutionPage";

vi.mock("../../api", () => ({
  api: {
    getTask: vi.fn(),
    executeTask: vi.fn()
  }
}));

afterEach(cleanup);

describe("ExecutionPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("reads a newly created task before executing it once", async () => {
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
    vi.mocked(api.getTask).mockResolvedValue({
      task_id: "task-exec-1",
      status: "created",
      doc_id: "doc-1",
      schema_id: "policy",
      schema_version: "1.0.0",
      template_id: "policy-template",
      template_version: "1.0.0",
      input_hash: "sha256:input",
      options: {},
      report_paths: {},
      package_zip_path: null
    });

    render(<ExecutionPage taskId="task-exec-1" />);

    await waitFor(() => expect(api.getTask).toHaveBeenCalledWith("task-exec-1"));
    expect(api.executeTask).toHaveBeenCalledTimes(1);
    expect(api.executeTask).toHaveBeenCalledWith("task-exec-1");
    expect(screen.queryByText("正在读取任务状态")).not.toBeInTheDocument();
    expect(screen.getByText("正在执行转换")).toBeInTheDocument();
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

  it("shows a completed task after remount without posting execute again", async () => {
    vi.mocked(api.getTask).mockResolvedValue({
      task_id: "task-completed-1",
      status: "completed",
      doc_id: "doc-1",
      schema_id: "policy",
      schema_version: "1.0.0",
      template_id: "policy-template",
      template_version: "1.0.0",
      input_hash: "sha256:input",
      options: {},
      report_paths: { mapping: "reports/mapping.json" },
      package_zip_path: "packages/task-completed-1.zip"
    });

    const firstMount = render(<ExecutionPage taskId="task-completed-1" />);
    expect(await screen.findByRole("link", { name: "查看任务详情" })).toHaveAttribute(
      "href",
      "/tasks/task-completed-1"
    );
    expect(screen.getByRole("status", { name: "已完成" })).toBeInTheDocument();
    expect(api.executeTask).not.toHaveBeenCalled();

    firstMount.unmount();
    render(<ExecutionPage taskId="task-completed-1" />);

    await waitFor(() => expect(api.getTask).toHaveBeenCalledTimes(2));
    expect(await screen.findByRole("link", { name: "查看任务详情" })).toHaveAttribute(
      "href",
      "/tasks/task-completed-1"
    );
    expect(api.executeTask).not.toHaveBeenCalled();
  });
});
