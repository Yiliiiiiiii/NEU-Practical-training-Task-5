// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./pages/task-detail/TaskDetailPage", () => ({
  TaskDetailPage: ({ taskId }: { taskId: string }) => (
    <section aria-label="任务详情内容">
      <h1>任务详情</h1>
      <p>当前任务：{taskId}</p>
    </section>
  )
}));

vi.mock("./pages/conversion/ConversionPage", () => ({
  ConversionPage: () => <h1>新建转换页面</h1>
}));

vi.mock("./pages/execution/ExecutionPage", () => ({
  ExecutionPage: () => <h1>执行转换页面</h1>
}));

vi.mock("./pages/overview/OverviewPage", () => ({
  OverviewPage: () => <h1>工作概览页面</h1>
}));

vi.mock("./pages/tasks/TasksPage", () => ({
  TasksPage: () => <h1>转换任务页面</h1>
}));

vi.mock("./pages/review/ReviewPage", () => ({
  ReviewPage: () => <h1>复核队列页面</h1>
}));

vi.mock("./pages/schemapacks/SchemaPacksPage", () => ({
  SchemaPacksPage: () => <h1>SchemaPacks 目录页面</h1>
}));

vi.mock("./pages/evidence/EvidencePage", () => ({
  EvidencePage: () => <h1>证据与评测页面</h1>
}));

vi.mock("./pages/settings/SettingsPage", () => ({
  SettingsPage: () => <h1>运行环境页面</h1>
}));

afterEach(cleanup);

describe("App route integration", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/tasks/task-direct");
  });

  it("renders a direct task-detail route inside the Chinese application shell", () => {
    render(<App />);

    expect(screen.getByRole("navigation", { name: "功能导航" })).toBeInTheDocument();
    expect(screen.getByRole("main", { name: "主工作区" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "任务详情" })).toBeInTheDocument();
    expect(screen.getByText("当前任务：task-direct")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "任务" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "新建转换" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "收起导航" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "收起导航" }));
    expect(screen.getByRole("button", { name: "展开导航" })).toBeInTheDocument();
    expect(screen.queryByText("Task details")).not.toBeInTheDocument();
  });

  it.each([
    ["/", "工作概览页面"],
    ["/conversions/new", "新建转换页面"],
    ["/conversions/executing/task-direct", "执行转换页面"],
    ["/tasks", "转换任务页面"],
    ["/review", "复核队列页面"],
    ["/schemapacks", "SchemaPacks 目录页面"],
    ["/evidence", "证据与评测页面"],
    ["/settings", "运行环境页面"]
  ])("dispatches %s to its integrated page", (pathname, heading) => {
    window.history.replaceState({}, "", pathname);
    render(<App />);

    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
  });
});
