// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../api";
import { ConversionPage } from "./ConversionPage";

vi.mock("../../api", () => ({
  api: {
    listSchemas: vi.fn(),
    listTemplates: vi.fn(),
    listExternalUirAdapters: vi.fn(),
    detectExternalUirAdapter: vi.fn(),
    importDocument: vi.fn(),
    convertExternalUir: vi.fn(),
    importExternalUir: vi.fn(),
    createTask: vi.fn(),
    createExternalUirTask: vi.fn(),
    executeTask: vi.fn()
  }
}));

const uirText = JSON.stringify({
  doc_id: "doc-1",
  metadata: { title: "政策示例" },
  blocks: [{ block_id: "b-1", type: "paragraph", text: "正文" }]
});

const externalAdapterReport = {
  adapter_id: "topic11",
  adapter_version: "1.0.0",
  source_system: "topic11",
  external_doc_id: "external-doc",
  generated_doc_id: "external-doc",
  status: "converted",
  trace_coverage: 1,
  block_count: 1,
  table_count: 0,
  warning_count: 0,
  error_count: 0,
  trace_items: [],
  assisted_suggestions: [],
  llm_used: true,
  llm_auto_accepted_count: 3,
  warnings: [],
  errors: [],
  raw_payload_hash: "adapter-sha"
};

const externalRouteReport = {
  selected_schema_id: "policy",
  selected_template_id: "policy-template",
  confidence: 0.92,
  reason: "命中确定性路由规则",
  alternatives: [],
  review_required: true,
  candidates: [{
    schema_id: "policy",
    template_id: "policy-template",
    confidence: 0.92,
    reasons: ["命中标题字段"],
    evidence: [],
    risk_flags: []
  }],
  decision_reason: "需要人工确认后才能创建任务",
  route_version: "1.0.0"
};

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
  vi.mocked(api.detectExternalUirAdapter).mockResolvedValue({
    selected_adapter: { adapter_id: "topic11", confidence: 0.88 },
    alternatives: [],
    review_required: false
  });
  vi.mocked(api.importDocument).mockResolvedValue({ doc_id: "imported-doc", status: "imported", block_count: 1 });
  vi.mocked(api.createTask).mockResolvedValue({ task_id: "task-1", status: "pending" });
  vi.mocked(api.createExternalUirTask).mockResolvedValue({
    task_id: "external-task-1",
    status: "pending",
    review_required: true,
    warnings: []
  });
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

  it("blocks progression until UIR validation and creates a normal UIR task before navigating", async () => {
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
    expect(api.createExternalUirTask).not.toHaveBeenCalled();
    expect(api.executeTask).not.toHaveBeenCalled();
    expect(window.location.pathname).toBe("/conversions/executing/task-1");
  });

  it("preserves imported External UIR route and adapter provenance when creating its task", async () => {
    vi.mocked(api.convertExternalUir).mockResolvedValue({
      standard_uir: JSON.parse(uirText),
      adapter_report: externalAdapterReport,
      route_report: externalRouteReport,
      warnings: [],
      errors: []
    });
    vi.mocked(api.importExternalUir).mockResolvedValue({
      doc_id: "external-doc",
      document: { doc_id: "external-doc", title: "外部文档", block_count: 1 },
      adapter_report: externalAdapterReport,
      route_report: externalRouteReport,
      warnings: []
    });
    render(<ConversionPage />);

    fireEvent.change(screen.getByRole("textbox", { name: "External UIR JSON" }), {
      target: { value: JSON.stringify({ id: "external-doc", chunks: [] }) }
    });
    fireEvent.click(screen.getByRole("button", { name: "转换并预览" }));

    await waitFor(() => expect(api.convertExternalUir).toHaveBeenCalledTimes(1));
    expect(screen.getByText("建议待人工处理（未自动采纳）")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "导入标准 UIR" }));
    await waitFor(() => expect(api.importExternalUir).toHaveBeenCalledTimes(1));

    fireEvent.click(await screen.findByRole("checkbox", { name: "已人工确认 Schema / 模板选择" }));
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));
    fireEvent.click(await screen.findByRole("radio", { name: /政策 Schema/ }));
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));
    fireEvent.click(screen.getByRole("button", { name: "运行转换" }));

    await waitFor(() => expect(api.createExternalUirTask).toHaveBeenCalledWith({
      doc_id: "external-doc",
      schema_id: "policy",
      template_id: "policy-template",
      options: expect.any(Object),
      route_report: expect.objectContaining({
        ...externalRouteReport,
        decision_reason: "已确认使用路由建议 policy / policy-template。"
      }),
      adapter_report: externalAdapterReport
    }));
    expect(api.createTask).not.toHaveBeenCalled();
    expect(api.executeTask).not.toHaveBeenCalled();
    expect(window.location.pathname).toBe("/conversions/executing/external-task-1");
  });

  it("invalidates external conversion state when its JSON input changes", async () => {
    vi.mocked(api.convertExternalUir).mockResolvedValue({
      standard_uir: JSON.parse(uirText),
      adapter_report: externalAdapterReport,
      route_report: externalRouteReport,
      warnings: [],
      errors: []
    });
    vi.mocked(api.importExternalUir).mockResolvedValue({
      doc_id: "external-doc",
      document: { doc_id: "external-doc", title: "外部文档", block_count: 1 },
      adapter_report: externalAdapterReport,
      route_report: externalRouteReport,
      warnings: []
    });
    render(<ConversionPage />);

    const externalJson = screen.getByRole("textbox", { name: "External UIR JSON" });
    fireEvent.change(externalJson, {
      target: { value: JSON.stringify({ id: "external-doc", chunks: [] }) }
    });
    fireEvent.click(screen.getByRole("button", { name: "检测适配器" }));
    expect(await screen.findByText("88%")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "转换并预览" }));

    const importButton = screen.getByRole("button", { name: "导入标准 UIR" });
    await waitFor(() => expect(importButton).toBeEnabled());
    fireEvent.click(importButton);
    await waitFor(() => expect(api.importExternalUir).toHaveBeenCalledTimes(1));
    fireEvent.click(await screen.findByRole("checkbox", { name: "已人工确认 Schema / 模板选择" }));
    expect(screen.getByRole("button", { name: "下一步" })).toBeEnabled();

    fireEvent.change(externalJson, {
      target: { value: JSON.stringify({ id: "external-doc-edited", chunks: [] }) }
    });

    expect(importButton).toBeDisabled();
    expect(screen.queryByText("88%")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: "已人工确认 Schema / 模板选择" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "下一步" })).toBeDisabled();
  });

  it("discards a conversion response that finishes after the external JSON changes", async () => {
    let resolveConversion!: (value: {
      standard_uir: Record<string, unknown>;
      adapter_report: typeof externalAdapterReport;
      route_report: typeof externalRouteReport;
      warnings: string[];
      errors: string[];
    }) => void;
    const conversion = new Promise<{
      standard_uir: Record<string, unknown>;
      adapter_report: typeof externalAdapterReport;
      route_report: typeof externalRouteReport;
      warnings: string[];
      errors: string[];
    }>((resolve) => {
      resolveConversion = resolve;
    });
    vi.mocked(api.convertExternalUir).mockReturnValue(conversion);
    render(<ConversionPage />);

    const externalJson = screen.getByRole("textbox", { name: "External UIR JSON" });
    fireEvent.change(externalJson, {
      target: { value: JSON.stringify({ id: "external-doc", chunks: [] }) }
    });
    fireEvent.click(screen.getByRole("button", { name: "转换并预览" }));
    await waitFor(() => expect(api.convertExternalUir).toHaveBeenCalledTimes(1));

    fireEvent.change(externalJson, {
      target: { value: JSON.stringify({ id: "external-doc-edited", chunks: [] }) }
    });
    await act(async () => {
      resolveConversion({
        standard_uir: JSON.parse(uirText),
        adapter_report: externalAdapterReport,
        route_report: externalRouteReport,
        warnings: [],
        errors: []
      });
    });

    expect(screen.getByRole("button", { name: "导入标准 UIR" })).toBeDisabled();
    expect(screen.queryByRole("checkbox", { name: "已人工确认 Schema / 模板选择" })).not.toBeInTheDocument();
  });

  it("invalidates an External UIR preview when any conversion option changes", async () => {
    vi.mocked(api.listExternalUirAdapters).mockResolvedValue({
      items: [{
        adapter_id: "topic11",
        adapter_version: "1.0.0",
        supported_dialects: [],
        source_systems: ["topic11"],
        supports_tables: true,
        supports_sections: true,
        supports_pages: true,
        supports_bbox: false,
        requires_llm: false,
        description: "adapter"
      }]
    });
    vi.mocked(api.convertExternalUir).mockResolvedValue({
      standard_uir: JSON.parse(uirText),
      adapter_report: externalAdapterReport,
      route_report: externalRouteReport,
      warnings: [],
      errors: []
    });
    render(<ConversionPage />);

    fireEvent.change(screen.getByRole("textbox", { name: "External UIR JSON" }), {
      target: { value: JSON.stringify({ id: "external-doc", chunks: [] }) }
    });

    const convertButton = screen.getByRole("button", { name: "转换并预览" });
    const importButton = screen.getByRole("button", { name: "导入标准 UIR" });
    const changes = [
      () => fireEvent.change(screen.getByLabelText("来源系统"), { target: { value: "topic12" } }),
      () => fireEvent.change(screen.getByLabelText("方言提示"), { target: { value: "topic11" } }),
      () => fireEvent.click(screen.getByRole("checkbox", { name: "启用确定性 Schema 路由" })),
      () => fireEvent.click(screen.getByRole("checkbox", { name: "允许 LLM 辅助" }))
    ];

    for (const change of changes) {
      fireEvent.click(convertButton);
      await waitFor(() => expect(importButton).toBeEnabled());
      change();
      expect(importButton).toBeDisabled();
    }
  });

  it("discards a late External UIR conversion after a conversion option changes", async () => {
    let resolveConversion!: (value: {
      standard_uir: Record<string, unknown>;
      adapter_report: typeof externalAdapterReport;
      route_report: typeof externalRouteReport;
      warnings: string[];
      errors: string[];
    }) => void;
    const conversion = new Promise<{
      standard_uir: Record<string, unknown>;
      adapter_report: typeof externalAdapterReport;
      route_report: typeof externalRouteReport;
      warnings: string[];
      errors: string[];
    }>((resolve) => {
      resolveConversion = resolve;
    });
    vi.mocked(api.convertExternalUir).mockReturnValue(conversion);
    render(<ConversionPage />);

    fireEvent.change(screen.getByRole("textbox", { name: "External UIR JSON" }), {
      target: { value: JSON.stringify({ id: "external-doc", chunks: [] }) }
    });
    fireEvent.click(screen.getByRole("button", { name: "转换并预览" }));
    await waitFor(() => expect(api.convertExternalUir).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("checkbox", { name: "允许 LLM 辅助" }));
    await act(async () => {
      resolveConversion({
        standard_uir: JSON.parse(uirText),
        adapter_report: externalAdapterReport,
        route_report: externalRouteReport,
        warnings: [],
        errors: []
      });
    });

    expect(screen.getByRole("button", { name: "导入标准 UIR" })).toBeDisabled();
    expect(screen.queryByRole("checkbox", { name: "已人工确认 Schema / 模板选择" })).not.toBeInTheDocument();
  });

  it("discards a late External UIR import after a conversion option changes", async () => {
    let resolveImport!: (value: {
      doc_id: string;
      document: { doc_id: string; title: string; block_count: number };
      adapter_report: typeof externalAdapterReport;
      route_report: typeof externalRouteReport;
      warnings: string[];
    }) => void;
    const imported = new Promise<{
      doc_id: string;
      document: { doc_id: string; title: string; block_count: number };
      adapter_report: typeof externalAdapterReport;
      route_report: typeof externalRouteReport;
      warnings: string[];
    }>((resolve) => {
      resolveImport = resolve;
    });
    vi.mocked(api.convertExternalUir).mockResolvedValue({
      standard_uir: JSON.parse(uirText),
      adapter_report: externalAdapterReport,
      route_report: externalRouteReport,
      warnings: [],
      errors: []
    });
    vi.mocked(api.importExternalUir).mockReturnValue(imported);
    render(<ConversionPage />);

    fireEvent.change(screen.getByRole("textbox", { name: "External UIR JSON" }), {
      target: { value: JSON.stringify({ id: "external-doc", chunks: [] }) }
    });
    fireEvent.click(screen.getByRole("button", { name: "转换并预览" }));
    const importButton = screen.getByRole("button", { name: "导入标准 UIR" });
    await waitFor(() => expect(importButton).toBeEnabled());
    fireEvent.click(importButton);
    await waitFor(() => expect(api.importExternalUir).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("checkbox", { name: "允许 LLM 辅助" }));
    await act(async () => {
      resolveImport({
        doc_id: "external-doc",
        document: { doc_id: "external-doc", title: "外部文档", block_count: 1 },
        adapter_report: externalAdapterReport,
        route_report: externalRouteReport,
        warnings: []
      });
    });

    expect(importButton).toBeDisabled();
    expect(screen.queryByRole("checkbox", { name: "已人工确认 Schema / 模板选择" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "下一步" })).toBeDisabled();
  });

  it("records a manually confirmed SchemaPack override in the external route task payload", async () => {
    const manualRouteReport = {
      ...externalRouteReport,
      candidates: [
        {
          ...externalRouteReport.candidates[0],
          evidence: [{
            evidence_type: "keyword" as const,
            value: "政策",
            source_path: "blocks[0].text",
            weight: 0.92,
            matched_schema: "policy"
          }]
        },
        {
          schema_id: "meeting",
          template_id: "meeting-template",
          confidence: 0.72,
          reasons: ["人工选择的候选项"],
          evidence: [],
          risk_flags: []
        }
      ]
    };
    vi.mocked(api.listSchemas).mockResolvedValue({
      items: [
        {
          schema_id: "policy",
          name: "政策 Schema",
          version: "1.0.0",
          status: "active",
          fields: []
        },
        {
          schema_id: "meeting",
          name: "会议 Schema",
          version: "1.0.0",
          status: "active",
          fields: []
        }
      ],
      total: 2
    });
    vi.mocked(api.listTemplates).mockResolvedValue({
      items: [
        {
          template_id: "policy-template",
          schema_id: "policy",
          name: "政策模板",
          version: "1.0.0",
          status: "active"
        },
        {
          template_id: "meeting-template",
          schema_id: "meeting",
          name: "会议模板",
          version: "1.0.0",
          status: "active"
        }
      ],
      total: 2
    });
    vi.mocked(api.convertExternalUir).mockResolvedValue({
      standard_uir: JSON.parse(uirText),
      adapter_report: externalAdapterReport,
      route_report: manualRouteReport,
      warnings: [],
      errors: []
    });
    vi.mocked(api.importExternalUir).mockResolvedValue({
      doc_id: "external-doc",
      document: { doc_id: "external-doc", title: "外部文档", block_count: 1 },
      adapter_report: externalAdapterReport,
      route_report: manualRouteReport,
      warnings: []
    });
    render(<ConversionPage />);

    fireEvent.change(screen.getByRole("textbox", { name: "External UIR JSON" }), {
      target: { value: JSON.stringify({ id: "external-doc", chunks: [] }) }
    });
    fireEvent.click(screen.getByRole("button", { name: "转换并预览" }));
    fireEvent.click(await screen.findByRole("button", { name: "导入标准 UIR" }));
    await waitFor(() => expect(api.importExternalUir).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole("checkbox", { name: "已人工确认 Schema / 模板选择" }));
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));
    fireEvent.click(await screen.findByRole("radio", { name: /会议 Schema/ }));
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));

    const schemaReview = screen.getByRole("heading", { name: "SchemaPack 复核" }).closest("section");
    expect(schemaReview).not.toBeNull();
    expect(within(schemaReview as HTMLElement).getByText("meeting")).toBeInTheDocument();
    expect(within(schemaReview as HTMLElement).getByText("meeting-template")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "运行转换" }));

    await waitFor(() => expect(api.createExternalUirTask).toHaveBeenCalledWith(expect.objectContaining({
      doc_id: "external-doc",
      schema_id: "meeting",
      template_id: "meeting-template",
      route_report: expect.objectContaining({
        selected_schema_id: "meeting",
        selected_template_id: "meeting-template",
        decision_reason: "人工确认选择 meeting / meeting-template；原始路由建议为 policy / policy-template。",
        candidates: expect.arrayContaining([
          expect.objectContaining({
            schema_id: "policy",
            evidence: expect.arrayContaining([
              expect.objectContaining({ value: "政策", source_path: "blocks[0].text" })
            ])
          })
        ])
      })
    })));
  });
});
