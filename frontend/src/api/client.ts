import type {
  CandidateListResponse,
  ConvertResponse,
  DocumentImportResponse,
  DocumentListResponse,
  DownloadResult,
  GenerateCandidatesResponse,
  JsonObject,
  MappingListResponse,
  MappingRunResponse,
  MappingTemplate,
  PackageResponse,
  ReportResponse,
  SchemaListResponse,
  TargetSchema,
  TaskCreateResponse,
  TaskDetailResponse,
  TaskListResponse,
  TemplateListResponse,
} from "./types";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

type RequestBody = unknown;

export function buildApiUrl(base: string, path: string): string {
  return `${base.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

export async function extractApiError(response: Response, label: string): Promise<string> {
  const prefix = `${label} failed (${response.status})`;
  const contentType = response.headers.get("content-type") ?? "";

  if (!contentType.includes("application/json")) {
    const text = await response.text();
    return text ? `${prefix}: ${text}` : prefix;
  }

  let body: unknown;
  try {
    body = (await response.json()) as unknown;
  } catch {
    return prefix;
  }
  if (isObject(body)) {
    if (typeof body.detail === "string") {
      return `${prefix}: ${body.detail}`;
    }
    if (isObject(body.error) && typeof body.error.message === "string") {
      return `${prefix}: ${body.error.message}`;
    }
  }
  return prefix;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  label = "API request",
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }

  const response = await fetch(buildApiUrl(API_BASE_URL, path), {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw new Error(await extractApiError(response, label));
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

function jsonBody(body: RequestBody): string {
  return JSON.stringify(body ?? {});
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export const api = {
  importDocument(uir: JsonObject) {
    return apiRequest<DocumentImportResponse>(
      "/documents/import",
      { method: "POST", body: jsonBody({ uir }) },
      "Import UIR",
    );
  },
  listDocuments() {
    return apiRequest<DocumentListResponse>("/documents", {}, "Load documents");
  },
  createSchema(schema: TargetSchema) {
    return apiRequest<{ schema_id: string; status: string }>(
      "/schemas",
      { method: "POST", body: jsonBody({ schema }) },
      "Create schema",
    );
  },
  listSchemas() {
    return apiRequest<SchemaListResponse>("/schemas", {}, "Load schemas");
  },
  getSchema(schemaId: string) {
    return apiRequest<TargetSchema>(`/schemas/${schemaId}`, {}, "Load schema");
  },
  createTemplate(template: MappingTemplate) {
    return apiRequest<{ template_id: string; status: string }>(
      "/templates",
      { method: "POST", body: jsonBody({ template }) },
      "Create template",
    );
  },
  listTemplates() {
    return apiRequest<TemplateListResponse>("/templates", {}, "Load templates");
  },
  getTemplate(templateId: string) {
    return apiRequest<MappingTemplate>(`/templates/${templateId}`, {}, "Load template");
  },
  createTask(payload: {
    doc_id: string;
    schema_id: string;
    template_id: string;
    schema_version?: string;
    template_version?: string;
    options?: JsonObject;
  }) {
    return apiRequest<TaskCreateResponse>(
      "/tasks",
      { method: "POST", body: jsonBody(payload) },
      "Create task",
    );
  },
  listTasks() {
    return apiRequest<TaskListResponse>("/tasks", {}, "Load tasks");
  },
  getTask(taskId: string) {
    return apiRequest<TaskDetailResponse>(`/tasks/${taskId}`, {}, "Load task");
  },
  generateCandidates(taskId: string) {
    return apiRequest<GenerateCandidatesResponse>(
      `/tasks/${taskId}/generate-candidates`,
      { method: "POST", body: jsonBody({}) },
      "Generate candidates",
    );
  },
  listCandidates(taskId: string) {
    return apiRequest<CandidateListResponse>(
      `/tasks/${taskId}/candidates`,
      {},
      "Load candidates",
    );
  },
  runMapping(taskId: string, reviewThreshold = 0.8, enableLlmFallback = false) {
    return apiRequest<MappingRunResponse>(
      `/tasks/${taskId}/map`,
      {
        method: "POST",
        body: jsonBody({
          enable_llm_fallback: enableLlmFallback,
          review_threshold: reviewThreshold,
        }),
      },
      "Run mapping",
    );
  },
  listMappings(taskId: string) {
    return apiRequest<MappingListResponse>(`/tasks/${taskId}/mappings`, {}, "Load mappings");
  },
  reviewMappings(
    taskId: string,
    reviews: Array<{
      mapping_id: string;
      new_target_field_id?: string | null;
      decision?: string;
      comment?: string | null;
      reviewer?: string;
    }>,
  ) {
    return apiRequest<{ task_id: string; updated: number; status: string }>(
      `/tasks/${taskId}/mappings/review`,
      { method: "POST", body: jsonBody({ reviews }) },
      "Save mapping review",
    );
  },
  convertTask(taskId: string) {
    return apiRequest<ConvertResponse>(
      `/tasks/${taskId}/convert`,
      { method: "POST", body: jsonBody({ render_outputs: true, chunk_size: 500 }) },
      "Convert task",
    );
  },
  getCanonical(taskId: string) {
    return apiRequest<ReportResponse>(`/tasks/${taskId}/canonical`, {}, "Load canonical");
  },
  getMappingReport(taskId: string) {
    return apiRequest<ReportResponse>(
      `/tasks/${taskId}/reports/mapping`,
      {},
      "Load mapping report",
    );
  },
  getValidationReport(taskId: string) {
    return apiRequest<ReportResponse>(
      `/tasks/${taskId}/reports/validation`,
      {},
      "Load validation report",
    );
  },
  getConsistencyReport(taskId: string) {
    return apiRequest<ReportResponse>(
      `/tasks/${taskId}/reports/consistency`,
      {},
      "Load consistency report",
    );
  },
  getPackageVerifierReport(taskId: string) {
    return apiRequest<ReportResponse>(
      `/tasks/${taskId}/reports/package-verifier`,
      {},
      "Load package verifier report",
    );
  },
  getTrace(taskId: string) {
    return apiRequest<ReportResponse>(`/tasks/${taskId}/trace`, {}, "Load trace");
  },
  createPackage(taskId: string, packageVersion = "1.0.0") {
    return apiRequest<PackageResponse>(
      `/tasks/${taskId}/package`,
      { method: "POST", body: jsonBody({ package_version: packageVersion }) },
      "Create package",
    );
  },
};

export async function downloadPackage(taskId: string): Promise<DownloadResult> {
  const response = await fetch(buildApiUrl(API_BASE_URL, `/tasks/${taskId}/package/download`));
  if (!response.ok) {
    throw new Error(await extractApiError(response, "Download package"));
  }
  return {
    blob: await response.blob(),
    sha256: response.headers.get("x-sha256"),
  };
}
