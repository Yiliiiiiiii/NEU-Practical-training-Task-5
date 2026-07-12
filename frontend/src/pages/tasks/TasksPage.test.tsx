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
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "beta" } });

    expect(screen.queryByText("task-alpha")).not.toBeInTheDocument();
    expect(screen.getByText("task-beta")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /task-beta$/ }));
    expect(window.location.pathname).toBe("/tasks/task-beta");
  });

  it("loads every API page before applying local filters", async () => {
    const firstPage = Array.from({ length: 100 }, (_, index) => ({
      task_id: `task-${index + 1}`,
      doc_id: `doc-${index + 1}`,
      schema_id: "notice",
      template_id: "notice-v1",
      status: "completed"
    }));
    const secondPage = Array.from({ length: 5 }, (_, index) => ({
      task_id: `task-${index + 101}`,
      doc_id: `doc-${index + 101}`,
      schema_id: "notice",
      template_id: "notice-v1",
      status: "completed"
    }));
    vi.mocked(api.listTasks).mockImplementation((page) =>
      Promise.resolve({ items: page === 1 ? firstPage : secondPage, total: 105 })
    );

    render(<TasksPage />);

    await screen.findByText("task-1");
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "task-105" } });

    expect(await screen.findByText("task-105")).toBeInTheDocument();
    expect(api.listTasks).toHaveBeenNthCalledWith(1, 1, 100);
    expect(api.listTasks).toHaveBeenNthCalledWith(2, 2, 100);
  });

  it("does not expose package downloads from a completed task list row", async () => {
    render(<TasksPage />);

    await screen.findByText("task-beta");

    expect(screen.queryByRole("link", { name: /Package/ })).not.toBeInTheDocument();
    expect(screen.getAllByText(/任务详情.*Package/)).toHaveLength(2);
    expect(api.packageDownloadUrl).not.toHaveBeenCalled();
  });
});
