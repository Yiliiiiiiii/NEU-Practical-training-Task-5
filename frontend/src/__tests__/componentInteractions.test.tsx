import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import type { MappingListItem } from "../api/types";
import { CodePanel } from "../components/CodePanel";
import { JsonWorkbench } from "../components/JsonWorkbench";
import { MappingTable } from "../components/MappingTable";
import { ReportTabs } from "../components/ReportTabs";

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("CodePanel", () => {
  it("renders an empty state and ignores copy without content", () => {
    render(<CodePanel emptyMessage="Nothing here" title="Empty JSON" value={null} />);

    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy panel JSON" })).toBeDisabled();
  });

  it("copies formatted JSON and resets its feedback icon", async () => {
    vi.useFakeTimers();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    render(<CodePanel title="Canonical" value={{ title: "Document" }} />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Copy panel JSON" }));
    });
    expect(writeText).toHaveBeenCalledWith('{\n  "title": "Document"\n}');

    act(() => {
      vi.advanceTimersByTime(1400);
    });
    expect(screen.getByTitle("Copy Canonical")).toBeInTheDocument();
  });
});

describe("JsonWorkbench", () => {
  it("edits text and imports a JSON file", async () => {
    const onChange = vi.fn();
    const { container } = render(
      <JsonWorkbench
        description="Edit JSON"
        error={null}
        id="json-test"
        onChange={onChange}
        title="Test JSON"
        value="{}"
      />,
    );

    fireEvent.change(screen.getByRole("textbox", { name: "Test JSON" }), {
      target: { value: '{"typed":true}' },
    });
    expect(onChange).toHaveBeenCalledWith('{"typed":true}');

    const file = new File(["file"], "input.json", { type: "application/json" });
    Object.defineProperty(file, "text", {
      configurable: true,
      value: vi.fn().mockResolvedValue('{"from":"file"}'),
    });
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(onChange).toHaveBeenCalledWith('{"from":"file"}'));
  });

  it("shows parser feedback", () => {
    render(
      <JsonWorkbench
        description="Edit JSON"
        error="Unexpected token"
        id="json-error"
        onChange={vi.fn()}
        title="Broken JSON"
        value="{"
      />,
    );
    expect(screen.getByText("Unexpected token")).toHaveClass("json-status--error");
  });
});

describe("mapping and report components", () => {
  const baseMapping: MappingListItem = {
    mapping_id: "mapping_1",
    task_id: "task_1",
    candidate_id: "candidate_1",
    source_name: "Title",
    source_path: "metadata.title",
    target_field_id: "title",
    target_field_name: "title",
    method: "exact_match",
    confidence: 1,
    status: "confirmed",
    need_review: false,
    evidence: [],
  };

  it("renders empty, confirmed, and custom mapping states", () => {
    const { rerender } = render(
      <MappingTable mappings={[]} onReview={vi.fn()} targetFields={[]} />,
    );
    expect(screen.getByText("No mappings yet.")).toBeInTheDocument();

    rerender(
      <MappingTable
        mappings={[
          baseMapping,
          {
            ...baseMapping,
            mapping_id: "mapping_2",
            source_name: "Summary",
            source_path: "metadata.summary",
            target_field_id: "summary",
            status: "reviewed",
          },
        ]}
        onReview={vi.fn()}
        targetFields={[]}
      />,
    );
    expect(screen.getByText("Confirmed")).toBeInTheDocument();
    expect(screen.getByText("reviewed")).toBeInTheDocument();
    expect(screen.getAllByRole("option").map((option) => option.textContent)).toEqual([
      "title",
      "summary",
      "title",
      "summary",
    ]);
  });

  it("switches among report payloads", () => {
    render(
      <ReportTabs
        reports={{
          mapping: { kind: "mapping" },
          validation: { kind: "validation" },
          consistency: { kind: "consistency" },
          trace: { kind: "trace" },
        }}
      />,
    );

    for (const label of ["Validation", "Consistency", "Trace", "Mapping"]) {
      fireEvent.click(screen.getByRole("button", { name: label }));
      expect(screen.getByText(new RegExp(`"kind": "${label.toLowerCase()}"`))).toBeInTheDocument();
    }
  });
});

describe("App toast lifecycle", () => {
  it("keeps the newest three messages, supports dismiss, and expires them", () => {
    vi.useFakeTimers();
    render(<App />);
    const refresh = screen.getByRole("button", { name: "Refresh" });

    fireEvent.click(refresh);
    fireEvent.click(refresh);
    fireEvent.click(refresh);
    fireEvent.click(refresh);
    expect(screen.getAllByText("Workbench ready")).toHaveLength(3);

    fireEvent.click(screen.getAllByRole("button", { name: "Dismiss Workbench ready" })[0]);
    expect(screen.getAllByText("Workbench ready")).toHaveLength(2);

    act(() => {
      vi.advanceTimersByTime(6000);
    });
    expect(screen.queryByText("Workbench ready")).not.toBeInTheDocument();
  });
});
