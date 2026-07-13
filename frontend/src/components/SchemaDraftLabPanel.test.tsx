// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { SchemaDraftLabPanel } from "./SchemaDraftLabPanel";

vi.mock("../api", () => ({
  api: {
    discoverSchemaDraftFields: vi.fn()
  }
}));

describe("SchemaDraftLabPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.discoverSchemaDraftFields).mockResolvedValue({
      sample_count: 1,
      field_candidates: [],
      warnings: [],
      llm_auto_accepted_count: 2
    });
  });

  afterEach(cleanup);

  it("treats any LLM bypass count as a safety failure instead of an acceptance claim", async () => {
    render(<SchemaDraftLabPanel />);

    fireEvent.change(screen.getByRole("textbox", { name: "Schema 草案样本 JSON" }), {
      target: { value: '[{"title":"示例"}]' }
    });
    fireEvent.click(screen.getByRole("button", { name: "发现字段" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("LLM 建议越过人工复核");
    expect(screen.getByText("安全失败")).toBeInTheDocument();
    expect(screen.queryByText("自动采纳")).not.toBeInTheDocument();
  });
});
