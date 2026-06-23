import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { api } from "../api/client";
import type { MappingListItem, TaskDetailResponse, TaskListItem } from "../api/types";
import type { WorkbenchSelection } from "../appTypes";
import { ImportPage } from "../pages/ImportPage";
import { MappingPage } from "../pages/MappingPage";
import { PackagePage } from "../pages/PackagePage";
import { TaskDetailPage } from "../pages/TaskDetailPage";
import { TasksPage } from "../pages/TasksPage";

const EMPTY_SELECTION: WorkbenchSelection = {
  docId: null,
  schemaId: null,
  templateId: null,
  taskId: null,
  taskStatus: null,
};

const ACTIVE_SELECTION: WorkbenchSelection = {
  docId: "doc_1",
  schemaId: "schema_1",
  templateId: "template_1",
  taskId: "task_1",
  taskStatus: "mapping_completed",
};

const TASK: TaskListItem = {
  task_id: "task_1",
  doc_id: "doc_1",
  schema_id: "schema_1",
  template_id: "template_1",
  status: "mapping_completed",
};

const TASK_DETAIL: TaskDetailResponse = {
  ...TASK,
  schema_version: "1.0.0",
  template_version: "1.0.0",
  input_hash: "sha256:test",
  options: {},
};

const MAPPING: MappingListItem = {
  mapping_id: "mapping_1",
  task_id: "task_1",
  candidate_id: "candidate_1",
  source_name: "Title",
  source_path: "metadata.title",
  target_field_id: "title",
  target_field_name: "title",
  method: "alias_match",
  confidence: 0.72,
  status: "pending_review",
  need_review: true,
  evidence: ["alias"],
};

beforeEach(() => {
  vi.spyOn(api, "listTasks").mockResolvedValue({ items: [], total: 0 });
  vi.spyOn(api, "getSchema").mockResolvedValue({
    schema_id: "schema_1",
    name: "Schema",
    version: "1.0.0",
    fields: [
      {
        field_id: "title",
        name: "title",
        display_name: "Title",
        type: "string",
        required: true,
        aliases: [],
        constraints: {},
      },
      {
        field_id: "summary",
        name: "summary",
        display_name: "Summary",
        type: "string",
        required: false,
        aliases: [],
        constraints: {},
      },
    ],
    json_schema: {},
  });
  vi.spyOn(api, "listCandidates").mockResolvedValue({ items: [] });
  vi.spyOn(api, "listMappings").mockResolvedValue({ items: [] });
  vi.spyOn(api, "generateCandidates").mockResolvedValue({
    task_id: "task_1",
    candidate_count: 2,
    status: "candidates_ready",
  });
  vi.spyOn(api, "runMapping").mockResolvedValue({
    task_id: "task_1",
    mapped_count: 1,
    review_required_count: 1,
    status: "review_required",
  });
  vi.spyOn(api, "reviewMappings").mockResolvedValue({
    task_id: "task_1",
    updated: 1,
    status: "review_saved",
  });
  vi.spyOn(api, "getTask").mockResolvedValue(TASK_DETAIL);
  vi.spyOn(api, "getCanonical").mockResolvedValue({ canonical_version: "1.0" });
  vi.spyOn(api, "getMappingReport").mockResolvedValue({ passed: true });
  vi.spyOn(api, "getValidationReport").mockResolvedValue({ passed: true });
  vi.spyOn(api, "getConsistencyReport").mockResolvedValue({ passed: true });
  vi.spyOn(api, "getPackageVerifierReport").mockResolvedValue({
    passed: true,
    summary: { verified_payloads: 9 },
    issues: [],
  });
  vi.spyOn(api, "getTrace").mockResolvedValue({ events: [] });
  vi.spyOn(api, "convertTask").mockResolvedValue({
    task_id: "task_1",
    status: "rendered",
    outputs: ["content.json", "content.md", "chunks.json"],
  });
  vi.spyOn(api, "createPackage").mockResolvedValue({
    package_id: "pkg_1",
    status: "completed",
    zip_path: "packages/pkg_1/standard_package.zip",
    sha256: "package-sha",
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("ImportPage", () => {
  it("creates a task from the active demo and publishes selection", async () => {
    vi.spyOn(api, "importDocument").mockResolvedValue({
      doc_id: "doc_1",
      status: "imported",
      block_count: 2,
    });
    vi.spyOn(api, "createSchema").mockResolvedValue({ schema_id: "schema_1", status: "created" });
    vi.spyOn(api, "createTemplate").mockResolvedValue({
      template_id: "template_1",
      status: "saved",
    });
    vi.spyOn(api, "createTask").mockResolvedValue({ task_id: "task_1", status: "created" });
    const onSelectionChange = vi.fn();
    const onToast = vi.fn();
    render(<ImportPage onSelectionChange={onSelectionChange} onToast={onToast} />);

    fireEvent.click(screen.getByRole("button", { name: "Create task" }));

    await waitFor(() => expect(onSelectionChange).toHaveBeenCalled());
    expect(onSelectionChange).toHaveBeenCalledWith({
      docId: "doc_1",
      schemaId: "schema_1",
      templateId: "template_1",
      taskId: "task_1",
      taskStatus: "created",
    });
    expect(await screen.findByText("Task task_1")).toBeInTheDocument();
    expect(onToast).toHaveBeenCalledWith(expect.objectContaining({ title: "Task created" }));
  });

  it("blocks invalid JSON, supports demo switching, and reports API failure", async () => {
    const onToast = vi.fn();
    render(<ImportPage onToast={onToast} />);

    fireEvent.click(screen.getByRole("button", { name: /Load policy demo/i }));
    expect(screen.getByRole("button", { name: /Load policy demo/i })).toHaveClass(
      "secondary-button--active",
    );
    const uirEditor = screen.getByRole("textbox", { name: "UIR Document" });
    fireEvent.change(uirEditor, { target: { value: "[]" } });
    expect(screen.getByText("JSON must be an object.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create task" })).toBeDisabled();

    fireEvent.change(uirEditor, { target: { value: "{" } });
    expect(uirEditor).toHaveAttribute("aria-invalid", "true");

    fireEvent.click(screen.getByRole("button", { name: /Load general demo/i }));
    vi.spyOn(api, "importDocument").mockRejectedValue("offline");
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));

    await waitFor(() =>
      expect(onToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: "Import failed", detail: "Unexpected import failure." }),
      ),
    );
  });
});

describe("TasksPage", () => {
  it("loads, refreshes, and opens a selected task", async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [TASK], total: 1 });
    const onSelectTask = vi.fn();
    const onToast = vi.fn();
    render(
      <TasksPage
        onSelectTask={onSelectTask}
        onToast={onToast}
        selectedTaskId="task_1"
      />,
    );

    expect(await screen.findByText("Current selection")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    expect(onSelectTask).toHaveBeenCalledWith(ACTIVE_SELECTION);
    expect(onToast).toHaveBeenCalledWith(expect.objectContaining({ title: "Task selected" }));

    fireEvent.click(screen.getByRole("button", { name: /Refresh tasks/i }));
    await waitFor(() => expect(api.listTasks).toHaveBeenCalledTimes(2));
  });

  it("keeps an empty state and reports load failures", async () => {
    vi.mocked(api.listTasks).mockRejectedValue(new Error("network down"));
    const onToast = vi.fn();
    render(<TasksPage onSelectTask={vi.fn()} onToast={onToast} selectedTaskId={null} />);

    expect(await screen.findByText("No tasks loaded.")).toBeInTheDocument();
    await waitFor(() =>
      expect(onToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: "Task list failed", detail: "network down" }),
      ),
    );
  });
});

describe("MappingPage", () => {
  it("generates candidates, runs mapping, and saves review", async () => {
    vi.mocked(api.listCandidates)
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValue({
        items: [
          {
            candidate_id: "candidate_1",
            task_id: "task_1",
            doc_id: "doc_1",
            source_path: "metadata.title",
            source_name: "Title",
            display_name: "Title",
            value_sample: "Document",
            inferred_type: "string",
            source_blocks: [],
            confidence: 1,
            evidence: [],
          },
        ],
      });
    vi.mocked(api.listMappings).mockResolvedValue({ items: [MAPPING] });
    const onSelectionChange = vi.fn();
    const onToast = vi.fn();
    render(
      <MappingPage
        onSelectionChange={onSelectionChange}
        onToast={onToast}
        selection={ACTIVE_SELECTION}
      />,
    );

    expect(await screen.findByText("Title")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Generate candidates/i }));
    expect(await screen.findByText("2 candidates generated")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Run mapping/i }));
    expect(await screen.findByText("1 mapped, 1 need review")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Target field for Title"), {
      target: { value: "summary" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() =>
      expect(api.reviewMappings).toHaveBeenCalledWith(
        "task_1",
        [expect.objectContaining({ mapping_id: "mapping_1", new_target_field_id: "summary" })],
      ),
    );
    expect(onSelectionChange).toHaveBeenCalledWith(
      expect.objectContaining({ taskStatus: "review_required" }),
    );
    expect(onToast).toHaveBeenCalledWith(expect.objectContaining({ title: "Review saved" }));
  });

  it("runs mapping with DeepSeek fallback enabled from the page control", async () => {
    render(
      <MappingPage
        onSelectionChange={vi.fn()}
        onToast={vi.fn()}
        selection={ACTIVE_SELECTION}
      />,
    );

    const fallbackToggle = await screen.findByRole("checkbox", {
      name: /DeepSeek fallback/i,
    });
    expect(fallbackToggle).toBeChecked();

    fireEvent.click(screen.getByRole("button", { name: /Run mapping/i }));

    await waitFor(() => expect(api.runMapping).toHaveBeenCalledWith("task_1", 0.8, true));
  });

  it("accepts a manual task ID and surfaces lookup failures", async () => {
    vi.mocked(api.getSchema).mockRejectedValue("schema unavailable");
    vi.mocked(api.listCandidates).mockRejectedValue(new Error("rows unavailable"));
    const onSelectionChange = vi.fn();
    const onToast = vi.fn();
    render(
      <MappingPage
        onSelectionChange={onSelectionChange}
        onToast={onToast}
        selection={{ ...EMPTY_SELECTION, schemaId: "schema_1" }}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("task_id"), { target: { value: "  manual  " } });
    fireEvent.click(screen.getByRole("button", { name: "Use task" }));
    expect(onSelectionChange).toHaveBeenCalledWith(
      expect.objectContaining({ taskId: "manual", taskStatus: "created" }),
    );
    await waitFor(() =>
      expect(onToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Schema fields unavailable",
          detail: "Target field lookup failed.",
        }),
      ),
    );
  });

  it("reports mutation failures instead of leaking rejected promises", async () => {
    vi.mocked(api.generateCandidates).mockRejectedValue(new Error("task busy"));
    const onToast = vi.fn();
    render(
      <MappingPage
        onSelectionChange={vi.fn()}
        onToast={onToast}
        selection={ACTIVE_SELECTION}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Generate candidates/i }));

    await waitFor(() =>
      expect(onToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: "Candidate generation failed", detail: "task busy" }),
      ),
    );
  });

  it("ignores a blank manual ID and uses success tone when review is unnecessary", async () => {
    vi.mocked(api.runMapping).mockResolvedValue({
      task_id: "task_1",
      mapped_count: 1,
      review_required_count: 0,
      status: "mapping_completed",
    });
    const onSelectionChange = vi.fn();
    const onToast = vi.fn();
    const { rerender } = render(
      <MappingPage
        onSelectionChange={onSelectionChange}
        onToast={onToast}
        selection={EMPTY_SELECTION}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Use task" }));
    expect(onSelectionChange).not.toHaveBeenCalled();

    rerender(
      <MappingPage
        onSelectionChange={onSelectionChange}
        onToast={onToast}
        selection={ACTIVE_SELECTION}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Run mapping/i }));
    await waitFor(() =>
      expect(onToast).toHaveBeenCalledWith(
        expect.objectContaining({ tone: "success", title: "Mapping completed" }),
      ),
    );
  });
});

describe("TaskDetailPage", () => {
  it("renders the no-selection state", () => {
    render(
      <TaskDetailPage
        onSelectionChange={vi.fn()}
        selection={EMPTY_SELECTION}
      />,
    );
    expect(screen.getByText("No task selected.")).toBeInTheDocument();
  });

  it("loads task evidence, tolerates optional report absence, and converts", async () => {
    vi.mocked(api.getValidationReport).mockRejectedValue(new Error("not generated"));
    const onSelectionChange = vi.fn();
    const onToast = vi.fn();
    render(
      <TaskDetailPage
        onSelectionChange={onSelectionChange}
        onToast={onToast}
        selection={ACTIVE_SELECTION}
      />,
    );

    expect(await screen.findByText(/canonical_version/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Convert task" }));

    await waitFor(() => expect(api.convertTask).toHaveBeenCalledWith("task_1"));
    expect(onSelectionChange).toHaveBeenCalledWith(
      expect.objectContaining({ taskStatus: "rendered" }),
    );
    expect(onToast).toHaveBeenCalledWith(expect.objectContaining({ title: "Conversion completed" }));
  });

  it("blocks review tasks and reports detail failures", async () => {
    vi.mocked(api.getTask).mockResolvedValue({ ...TASK_DETAIL, status: "review_required" });
    const onToast = vi.fn();
    const { rerender } = render(
      <TaskDetailPage
        onSelectionChange={vi.fn()}
        onToast={onToast}
        selection={{ ...ACTIVE_SELECTION, taskStatus: "review_required" }}
      />,
    );
    expect(await screen.findByText(/Resolve mapping review/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Convert task" })).toBeDisabled();

    vi.mocked(api.getTask).mockRejectedValue("unknown failure");
    rerender(
      <TaskDetailPage
        onSelectionChange={vi.fn()}
        onToast={onToast}
        selection={{ ...ACTIVE_SELECTION, taskId: "task_2" }}
      />,
    );
    await waitFor(() =>
      expect(onToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Task detail failed",
          detail: "Unexpected task detail failure.",
        }),
      ),
    );
  });

  it("reports conversion failures and keeps the current task visible", async () => {
    vi.mocked(api.convertTask).mockRejectedValue(new Error("conversion blocked"));
    const onToast = vi.fn();
    render(
      <TaskDetailPage
        onSelectionChange={vi.fn()}
        onToast={onToast}
        selection={ACTIVE_SELECTION}
      />,
    );
    await screen.findByText(/canonical_version/);
    fireEvent.click(screen.getByRole("button", { name: "Convert task" }));

    await waitFor(() =>
      expect(onToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: "Conversion failed", detail: "conversion blocked" }),
      ),
    );
    expect(screen.getByText("task_1")).toBeInTheDocument();
  });
});

describe("PackagePage", () => {
  it("renders no-task and not-ready states", () => {
    const { rerender } = render(
      <PackagePage onSelectionChange={vi.fn()} selection={EMPTY_SELECTION} />,
    );
    expect(screen.getByText("No task selected.")).toBeInTheDocument();

    rerender(
      <PackagePage
        onSelectionChange={vi.fn()}
        selection={{ ...ACTIVE_SELECTION, taskStatus: "created" }}
      />,
    );
    expect(screen.getByText(/Convert the task successfully/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Build package" })).toBeDisabled();
  });

  it("builds and downloads a package with SHA evidence", async () => {
    const onSelectionChange = vi.fn();
    const onToast = vi.fn();
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:package"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("zip", { status: 200, headers: { "x-sha256": "download-sha" } }),
      ),
    );
    render(
      <PackagePage
        onSelectionChange={onSelectionChange}
        onToast={onToast}
        selection={{ ...ACTIVE_SELECTION, taskStatus: "rendered" }}
      />,
    );

    fireEvent.change(screen.getByLabelText("Package version"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Build package" }));
    expect(await screen.findByText("pkg_1")).toBeInTheDocument();
    expect(api.createPackage).toHaveBeenCalledWith("task_1", "1.0.0");
    expect(onSelectionChange).toHaveBeenCalledWith(
      expect.objectContaining({ taskStatus: "completed" }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Download ZIP" }));
    expect(await screen.findByText("download-sha")).toBeInTheDocument();
    expect(clickSpy).toHaveBeenCalled();
    expect(onToast).toHaveBeenCalledWith(expect.objectContaining({ title: "Download started" }));
  });

  it("shows the external verifier report after building a package", async () => {
    vi.mocked(api.getPackageVerifierReport).mockResolvedValue({
      passed: true,
      summary: { verified_payloads: 9 },
      issues: [],
    });
    render(
      <PackagePage
        onSelectionChange={vi.fn()}
        onToast={vi.fn()}
        selection={{ ...ACTIVE_SELECTION, taskStatus: "rendered" }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Build package" }));

    expect(await screen.findByText("Verifier passed")).toBeInTheDocument();
    expect(screen.getByText(/9 payloads, 0 issues/i)).toBeInTheDocument();
    expect(api.getPackageVerifierReport).toHaveBeenCalledWith("task_1");
  });

  it("shows a package summary and standard file list after packaging", async () => {
    render(
      <PackagePage
        onSelectionChange={vi.fn()}
        onToast={vi.fn()}
        selection={{ ...ACTIVE_SELECTION, taskStatus: "rendered" }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Build package" }));

    expect(await screen.findByText("Package Summary")).toBeInTheDocument();
    expect(screen.getByText("manifest.json")).toBeInTheDocument();
    expect(screen.getByText("content.json")).toBeInTheDocument();
    expect(screen.getByText("trace.json")).toBeInTheDocument();
  });

  it("reports package creation failures", async () => {
    vi.mocked(api.createPackage).mockRejectedValue(new Error("validation blocked"));
    const onToast = vi.fn();
    render(
      <PackagePage
        onSelectionChange={vi.fn()}
        onToast={onToast}
        selection={{ ...ACTIVE_SELECTION, taskStatus: "rendered" }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Build package" }));
    await waitFor(() =>
      expect(onToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: "Packaging failed", detail: "validation blocked" }),
      ),
    );
  });

  it("reports download failures after a successful package build", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("missing", { status: 404 })));
    const onToast = vi.fn();
    render(
      <PackagePage
        onSelectionChange={vi.fn()}
        onToast={onToast}
        selection={{ ...ACTIVE_SELECTION, taskStatus: "rendered" }}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Build package" }));
    fireEvent.click(await screen.findByRole("button", { name: "Download ZIP" }));

    await waitFor(() =>
      expect(onToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: "Download failed", detail: expect.stringContaining("404") }),
      ),
    );
  });

  it("downloads without a SHA header using the filename fallback", async () => {
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:package"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("zip", { status: 200 })));
    const onToast = vi.fn();
    render(
      <PackagePage
        onSelectionChange={vi.fn()}
        onToast={onToast}
        selection={{ ...ACTIVE_SELECTION, taskStatus: "completed" }}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Build package" }));
    fireEvent.click(await screen.findByRole("button", { name: "Download ZIP" }));

    await waitFor(() =>
      expect(onToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: "Download started", detail: "standard_package.zip" }),
      ),
    );
  });
});

describe("App workflow shell", () => {
  it("navigates every desktop workbench view and emits refresh feedback", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /Tasks Inspect/i }));
    expect(screen.getByRole("heading", { name: "Tasks" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Mapping Review/i }));
    expect(screen.getByRole("heading", { name: "Mapping review" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Detail Read/i }));
    expect(screen.getByText("Open a task from Tasks before inspecting canonical output.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Package Create/i }));
    expect(screen.getByText("Open and convert a task before creating a standard package.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    expect(screen.getByText("Workbench ready")).toBeInTheDocument();
  });

  it.each(["candidates_ready", "review_required", "mapping_completed", "rendered", "completed"])(
    "selects a %s task and updates workflow state",
    async (status) => {
      vi.mocked(api.listTasks).mockResolvedValue({ items: [{ ...TASK, status }], total: 1 });
      render(<App />);
      fireEvent.click(screen.getByRole("button", { name: /Tasks/i }));
      fireEvent.click(await screen.findByRole("button", { name: "Open" }));

      expect(await screen.findByRole("heading", { name: "Mapping review" })).toBeInTheDocument();
      expect(screen.getByText("Task task_1")).toBeInTheDocument();
    },
  );
});
