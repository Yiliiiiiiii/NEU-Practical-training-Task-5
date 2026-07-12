// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../api";
import { TasksPage } from "./TasksPage";

vi.mock("../../api", () => ({
  api: {
    listTasks: vi.fn(),
    packageDownloadUrl: vi.fn((taskId: string) => `/downloads/${taskId}`)
  }
}));

describe("TasksPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.replaceState({}, "", "/tasks");
    vi.mocked(api.listTasks).mockResolvedValue({
      items: [
        {
          task_id: "task-alpha",
          doc_id: "doc-alpha",
          schema_id: "meeting",
          template_id: "meeting-v1",
          status: "pending"
        },
        {
          task_id: "task-beta",
          doc_id: "doc-beta",
          schema_id: "invoice",
          template_id: "invoice-v2",
          status: "completed"
        }
      ],
      total: 2
    });
  });

  afterEach(cleanup);

  it("filters the task table and opens the selected task route", async () => {
    render(<TasksPage />);

    expect(await screen.findByText("task-alpha")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("搜索任务"), {
      target: { value: "beta" }
    });

    expect(screen.queryByText("task-alpha")).not.toBeInTheDocument();
    expect(screen.getByText("task-beta")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "打开 task-beta" }));
    expect(window.location.pathname).toBe("/tasks/task-beta");
  });
});
