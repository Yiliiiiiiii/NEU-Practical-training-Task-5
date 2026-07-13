// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ConversionInputStep } from "./ConversionInputStep";

vi.mock("../../components/ExternalUirPanel", () => ({
  ExternalUirPanel: () => <div>External UIR panel</div>
}));

describe("ConversionInputStep", () => {
  it("uses roving focus and selection for ArrowLeft, ArrowRight, Home, and End", () => {
    render(
      <ConversionInputStep
        text=""
        validation={null}
        importedDocId=""
        working={false}
        onTextChange={vi.fn()}
        onExternalStandardPreview={vi.fn()}
        onExternalInputChange={vi.fn()}
        onValidate={vi.fn()}
        onImport={vi.fn().mockResolvedValue(undefined)}
        onExternalImported={vi.fn()}
        onRecommendedRoute={vi.fn()}
        onRouteConfirmationChange={vi.fn()}
      />
    );

    const paste = screen.getByRole("tab", { name: "粘贴 UIR" });
    const external = screen.getByRole("tab", { name: "External UIR" });
    const example = screen.getByRole("tab", { name: "示例" });

    expect(external).toHaveAttribute("tabindex", "0");
    expect(paste).toHaveAttribute("tabindex", "-1");
    external.focus();

    fireEvent.keyDown(external, { key: "ArrowRight" });
    expect(example).toHaveFocus();
    expect(example).toHaveAttribute("aria-selected", "true");
    expect(example).toHaveAttribute("tabindex", "0");

    fireEvent.keyDown(example, { key: "Home" });
    expect(paste).toHaveFocus();
    expect(paste).toHaveAttribute("aria-selected", "true");

    fireEvent.keyDown(paste, { key: "End" });
    expect(example).toHaveFocus();
    expect(example).toHaveAttribute("aria-selected", "true");

    fireEvent.keyDown(example, { key: "ArrowLeft" });
    expect(external).toHaveFocus();
    expect(external).toHaveAttribute("aria-selected", "true");
  });
});
