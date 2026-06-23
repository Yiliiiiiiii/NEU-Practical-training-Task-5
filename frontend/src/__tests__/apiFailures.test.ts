import { afterEach, describe, expect, it, vi } from "vitest";

import {
  API_BASE_URL,
  api,
  apiRequest,
  buildApiUrl,
  downloadPackage,
  extractApiError,
} from "../api/client";
import type { JsonObject, MappingTemplate, TargetSchema } from "../api/types";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("API failure normalization", () => {
  it("reads the unified error envelope", async () => {
    const response = new Response(
      JSON.stringify({ error: { code: "NOT_FOUND", message: "task not found", details: [] } }),
      { status: 404, headers: { "content-type": "application/json" } },
    );

    await expect(extractApiError(response, "加载 Task")).resolves.toBe(
      "加载 Task 失败 (404): task not found",
    );
  });

  it.each([
    ["plain text", new Response("backend offline", { status: 503 }), "请求 失败 (503): backend offline"],
    ["empty text", new Response("", { status: 503 }), "请求 失败 (503)"],
    [
      "legacy detail",
      new Response(JSON.stringify({ detail: "legacy error" }), {
        status: 400,
        headers: { "content-type": "application/json" },
      }),
      "请求 失败 (400): legacy error",
    ],
    [
      "unknown JSON",
      new Response(JSON.stringify({ message: "not contracted" }), {
        status: 500,
        headers: { "content-type": "application/json" },
      }),
      "请求 失败 (500)",
    ],
  ])("handles %s responses", async (_name, response, expected) => {
    await expect(extractApiError(response as Response, "请求")).resolves.toBe(expected);
  });

  it("falls back safely when a JSON response body is malformed", async () => {
    const response = new Response("{broken", {
      status: 502,
      headers: { "content-type": "application/json" },
    });

    await expect(extractApiError(response, "请求")).resolves.toBe("请求 失败 (502)");
  });
});

describe("apiRequest", () => {
  it("adds JSON content type, joins URLs, and parses the response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      apiRequest<{ ok: boolean }>("/tasks", { method: "POST", body: "{}" }),
    ).resolves.toEqual({ ok: true });

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(buildApiUrl(API_BASE_URL, "/tasks"));
    expect(new Headers(options.headers).get("content-type")).toBe("application/json");
  });

  it("preserves explicit headers and supports 204 responses", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      apiRequest<void>(
        "/tasks",
        { method: "POST", body: "raw", headers: { "content-type": "text/plain" } },
      ),
    ).resolves.toBeUndefined();
    const options = fetchMock.mock.calls[0][1] as RequestInit;
    expect(new Headers(options.headers).get("content-type")).toBe("text/plain");
  });

  it("throws normalized API failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { message: "busy" } }), {
          status: 409,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    await expect(apiRequest("/tasks/task/convert", {}, "Convert Task")).rejects.toThrow(
      "Convert Task 失败 (409): busy",
    );
  });
});

describe("API method surface", () => {
  it("routes every JSON API method through the expected endpoint", async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({}), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const schema = {
      schema_id: "schema",
      name: "Schema",
      version: "1.0.0",
      fields: [],
      json_schema: {},
    } as unknown as TargetSchema;
    const template = {
      template_id: "template",
      schema_id: "schema",
      name: "Template",
      version: "1.0.0",
      aliases: {},
      regex_rules: [],
      transform_rules: [],
      defaults: {},
      enum_maps: {},
    } as MappingTemplate;

    await api.importDocument({ doc_id: "doc" } as JsonObject);
    await api.listDocuments();
    await api.createSchema(schema);
    await api.listSchemas();
    await api.getSchema("schema");
    await api.createTemplate(template);
    await api.listTemplates();
    await api.getTemplate("template");
    await api.createTask({ doc_id: "doc", schema_id: "schema", template_id: "template" });
    await api.listTasks();
    await api.getTask("task");
    await api.generateCandidates("task");
    await api.listCandidates("task");
    await api.runMapping("task", 0.95, true);
    await api.listMappings("task");
    await api.reviewMappings("task", [{ mapping_id: "mapping", decision: "confirmed" }]);
    await api.convertTask("task");
    await api.getCanonical("task");
    await api.getMappingReport("task");
    await api.getValidationReport("task");
    await api.getConsistencyReport("task");
    await api.getTrace("task");
    await api.createPackage("task", "2.0.0");
    await api.getPackageVerifierReport("task");

    const paths = fetchMock.mock.calls.map(([url]) => String(url).replace(`${API_BASE_URL}/`, ""));
    expect(paths).toEqual([
      "documents/import",
      "documents",
      "schemas",
      "schemas",
      "schemas/schema",
      "templates",
      "templates",
      "templates/template",
      "tasks",
      "tasks",
      "tasks/task",
      "tasks/task/generate-candidates",
      "tasks/task/candidates",
      "tasks/task/map",
      "tasks/task/mappings",
      "tasks/task/mappings/review",
      "tasks/task/convert",
      "tasks/task/canonical",
      "tasks/task/reports/mapping",
      "tasks/task/reports/validation",
      "tasks/task/reports/consistency",
      "tasks/task/trace",
      "tasks/task/package",
      "tasks/task/reports/package-verifier",
    ]);
    const mappingBody = JSON.parse((fetchMock.mock.calls[13][1] as RequestInit).body as string);
    expect(mappingBody.review_threshold).toBe(0.95);
    expect(mappingBody.enable_llm_fallback).toBe(true);
  });

  it("downloads ZIP bytes and SHA evidence", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("zip", {
          status: 200,
          headers: { "x-sha256": "sha256-value" },
        }),
      ),
    );

    const result = await downloadPackage("task");

    expect(await result.blob.text()).toBe("zip");
    expect(result.sha256).toBe("sha256-value");
  });

  it("normalizes download failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("missing", { status: 404 })));

    await expect(downloadPackage("missing")).rejects.toThrow(
      "下载 Package 失败 (404): missing",
    );
  });
});
