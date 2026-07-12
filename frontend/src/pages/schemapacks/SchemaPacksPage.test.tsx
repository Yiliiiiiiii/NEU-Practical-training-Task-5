// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../api";
import { SchemaPacksPage } from "./SchemaPacksPage";

vi.mock("../../api", () => ({
  api: {
    listSchemas: vi.fn(),
    listTemplates: vi.fn()
  }
}));

vi.mock("../../components/SchemaDraftLabPanel", () => ({
  SchemaDraftLabPanel: () => <p>Schema Draft content</p>
}));

describe("SchemaPacksPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listSchemas).mockResolvedValue({
      items: [{ schema_id: "notice", name: "Notice", version: "1", fields: [] }],
      total: 1
    });
    vi.mocked(api.listTemplates).mockResolvedValue({
      items: [{ template_id: "notice-v1", schema_id: "notice", name: "Notice v1", version: "1" }],
      total: 1
    });
  });

  afterEach(cleanup);

  it("links tabs to tabpanels and supports standard tab keyboard navigation", async () => {
    render(<SchemaPacksPage />);

    await screen.findAllByText("Notice");
    const tabs = screen.getAllByRole("tab");
    expect(tabs[0]).toHaveAttribute("aria-controls", "schemapacks-panel-catalog");
    expect(screen.getByRole("tabpanel")).toHaveAttribute("id", "schemapacks-panel-catalog");

    fireEvent.keyDown(tabs[0], { key: "ArrowRight" });
    expect(tabs[1]).toHaveAttribute("aria-selected", "true");
    expect(document.activeElement).toBe(tabs[1]);

    fireEvent.keyDown(tabs[1], { key: "Home" });
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");

    fireEvent.keyDown(tabs[0], { key: "End" });
    expect(tabs[1]).toHaveAttribute("aria-selected", "true");

    fireEvent.keyDown(tabs[1], { key: "ArrowLeft" });
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
  });
});
