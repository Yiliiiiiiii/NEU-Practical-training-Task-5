// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../api";
import { ConversionPage } from "./ConversionPage";

vi.mock("../../api", () => ({
  api: {
    listSchemas: vi.fn(),
    listTemplates: vi.fn(),
    listExternalUirAdapters: vi.fn(),
    importDocument: vi.fn(),
    createTask: vi.fn(),
    executeTask: vi.fn()
  }
}));

const uirText = JSON.stringify({
  doc_id: "doc-1",
  metadata: { title: "政策示例" },
  blocks: [{ block_id: "b-1", type: "paragraph", text: "正文" }]
});

beforeEach(() => {
  window.history.replaceState({}, "", "/conversions/new");
  window.sessionStorage.clear();
  vi.clearAllMocks();
  vi.mocked(api.listSchemas).mockResolvedValue({
    items: [
      {
        schema_id: "policy",
        name: "政策 Schema",
        version: "1.0.0",
        status: "active",
        fields: [{ field_id: "title", name: "title", display_name: "标题", type: "string", required: true, aliases: [] }]
      }
    ],
    total: 1
  });
  vi.mocked(api.listTemplates).mockResolvedValue({
    items: [
      {
        template_id: "policy-template",
        schema_id: "policy",
        name: "政策模板",
        version: "1.0.0",
        status: "active",
        aliases: { title: ["标题"] }
      }
    ],
    total: 1
  });
  vi.mocked(api.listExternalUirAdapters).mockResolvedValue({ items: [] });
  vi.mocked(api.importDocument).mockResolvedValue({ doc_id: "imported-doc", status: "imported", block_count: 1 });
  vi.mocked(api.createTask).mockResolvedValue({ task_id: "task-1", status: "pending" });
  vi.mocked(api.executeTask).mockResolvedValue({
    task_id: "task-1",
    status: "completed",
    report_paths: {},
    package_zip_path: null,
    review_required_count: 0,
    unmapped_required_count: 0
  });
});

afterEach(cleanup);

describe("ConversionPage", () => {
  it("labels the JSON input and announces invalid UIR as an alert", () => {
    render(<ConversionPage />);

    expect(screen.getByRole("tablist", { name: "输入方式" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "粘贴 UIR" }));
    fireEvent.change(screen.getByRole("textbox", { name: "UIR JSON" }), {
      target: { value: "{" }
    });
    fireEvent.click(screen.getByRole("button", { name: "校验 UIR" }));

    expect(screen.getByRole("alert")).toHaveTextContent("JSON 格式无效。");
  });

  it("blocks progression until UIR validation and runs the normal UIR task sequence", async () => {
    render(<ConversionPage />);

    expect(screen.getByRole("button", { name: "下一步" })).toBeDisabled();
    fireEvent.click(screen.getByRole("tab", { name: "粘贴 UIR" }));
    fireEvent.change(screen.getByRole("textbox", { name: "UIR JSON" }), { target: { value: uirText } });
    fireEvent.click(screen.getByRole("button", { name: "校验 UIR" }));
    expect(screen.getByText("UIR 校验通过：doc-1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "下一步" }));
    const pack = await screen.findByRole("radio", { name: /政策 Schema/ });
    fireEvent.click(pack);
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));
    expect(screen.getByRole("heading", { name: "配置转换" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "下一步" }));
    fireEvent.click(screen.getByRole("button", { name: "运行转换" }));

    await waitFor(() => expect(api.importDocument).toHaveBeenCalledWith(JSON.parse(uirText)));
    expect(api.createTask).toHaveBeenCalledWith(expect.objectContaining({
      doc_id: "imported-doc",
      schema_id: "policy",
      template_id: "policy-template"
    }));
    expect(api.executeTask).toHaveBeenCalledWith("task-1");
    expect(window.location.pathname).toBe("/conversions/executing/task-1");
  });
});
