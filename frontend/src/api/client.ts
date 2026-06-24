import type {
  CandidateDecisionPayload,
  CandidateListResponse,
  ConvertResponse,
  DocumentImportResponse,
  DocumentListResponse,
  DownloadResult,
  GenerateCandidatesResponse,
  JsonObject,
  KnowledgeMetricsResponse,
  KnowledgePackCreatePayload,
  KnowledgePackItem,
  KnowledgePackListResponse,
  LearningCandidateItem,
  LearningCandidateListResponse,
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
  const prefix = `${label} 失败 (${response.status})`;
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
  label = "API 请求",
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
      "导入 UIR",
    );
  },
  listDocuments() {
    return apiRequest<DocumentListResponse>("/documents", {}, "加载 documents");
  },
  createSchema(schema: TargetSchema) {
    return apiRequest<{ schema_id: string; status: string }>(
      "/schemas",
      { method: "POST", body: jsonBody({ schema }) },
      "创建 Schema",
    );
  },
  listSchemas() {
    return apiRequest<SchemaListResponse>("/schemas", {}, "加载 schemas");
  },
  getSchema(schemaId: string) {
    return apiRequest<TargetSchema>(`/schemas/${schemaId}`, {}, "加载 Schema");
  },
  createTemplate(template: MappingTemplate) {
    return apiRequest<{ template_id: string; status: string }>(
      "/templates",
      { method: "POST", body: jsonBody({ template }) },
      "创建 Template",
    );
  },
  listTemplates() {
    return apiRequest<TemplateListResponse>("/templates", {}, "加载 templates");
  },
  getTemplate(templateId: string) {
    return apiRequest<MappingTemplate>(`/templates/${templateId}`, {}, "加载 Template");
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
      "创建 Task",
    );
  },
  listTasks() {
    return apiRequest<TaskListResponse>("/tasks", {}, "加载 Task");
  },
  getTask(taskId: string) {
    return apiRequest<TaskDetailResponse>(`/tasks/${taskId}`, {}, "加载 Task");
  },
  generateCandidates(taskId: string) {
    return apiRequest<GenerateCandidatesResponse>(
      `/tasks/${taskId}/generate-candidates`,
      { method: "POST", body: jsonBody({}) },
      "生成候选字段",
    );
  },
  listCandidates(taskId: string) {
    return apiRequest<CandidateListResponse>(
      `/tasks/${taskId}/candidates`,
      {},
      "加载候选字段",
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
      "执行 Mapping",
    );
  },
  listMappings(taskId: string) {
    return apiRequest<MappingListResponse>(`/tasks/${taskId}/mappings`, {}, "加载 Mapping");
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
      "保存 Mapping 审核",
    );
  },
  convertTask(taskId: string) {
    return apiRequest<ConvertResponse>(
      `/tasks/${taskId}/convert`,
      { method: "POST", body: jsonBody({ render_outputs: true, chunk_size: 500 }) },
      "Convert Task",
    );
  },
  getCanonical(taskId: string) {
    return apiRequest<ReportResponse>(`/tasks/${taskId}/canonical`, {}, "加载 Canonical");
  },
  getMappingReport(taskId: string) {
    return apiRequest<ReportResponse>(
      `/tasks/${taskId}/reports/mapping`,
      {},
      "加载 Mapping report",
    );
  },
  getValidationReport(taskId: string) {
    return apiRequest<ReportResponse>(
      `/tasks/${taskId}/reports/validation`,
      {},
      "加载 Validation report",
    );
  },
  getConsistencyReport(taskId: string) {
    return apiRequest<ReportResponse>(
      `/tasks/${taskId}/reports/consistency`,
      {},
      "加载 Consistency report",
    );
  },
  getPackageVerifierReport(taskId: string) {
    return apiRequest<ReportResponse>(
      `/tasks/${taskId}/reports/package-verifier`,
      {},
      "加载 Package verifier report",
    );
  },
  getTrace(taskId: string) {
    return apiRequest<ReportResponse>(`/tasks/${taskId}/trace`, {}, "加载 Trace");
  },
  createPackage(taskId: string, packageVersion = "1.0.0") {
    return apiRequest<PackageResponse>(
      `/tasks/${taskId}/package`,
      { method: "POST", body: jsonBody({ package_version: packageVersion }) },
      "生成 Package",
    );
  },
  captureKnowledgeRun(taskId: string) {
    return apiRequest<{ real_run_id: string }>(
      `/knowledge/real-runs/from-task/${taskId}`,
      { method: "POST", body: jsonBody({}) },
      "捕获真实运行",
    );
  },
  deriveKnowledgeCandidates(realRunId: string) {
    return apiRequest<LearningCandidateListResponse>(
      `/knowledge/real-runs/${realRunId}/derive`,
      { method: "POST", body: jsonBody({}) },
      "生成学习候选",
    );
  },
  listKnowledgeCandidates(status = "pending") {
    return apiRequest<LearningCandidateListResponse>(
      `/knowledge/candidates?status=${encodeURIComponent(status)}`,
      {},
      "加载学习候选",
    );
  },
  decideKnowledgeCandidate(candidateId: string, payload: CandidateDecisionPayload) {
    return apiRequest<LearningCandidateItem>(
      `/knowledge/candidates/${candidateId}/decision`,
      { method: "POST", body: jsonBody(payload) },
      "审核学习候选",
    );
  },
  createKnowledgePack(payload: KnowledgePackCreatePayload) {
    return apiRequest<KnowledgePackItem>(
      "/knowledge/packs",
      { method: "POST", body: jsonBody(payload) },
      "创建知识包",
    );
  },
  listKnowledgePacks() {
    return apiRequest<KnowledgePackListResponse>("/knowledge/packs", {}, "加载知识包");
  },
  activateKnowledgePack(packId: string) {
    return apiRequest<KnowledgePackItem>(
      `/knowledge/packs/${packId}/activate`,
      { method: "POST", body: jsonBody({}) },
      "启用知识包",
    );
  },
  getKnowledgeMetrics() {
    return apiRequest<KnowledgeMetricsResponse>("/knowledge/metrics", {}, "加载成长指标");
  },
};

export async function downloadPackage(taskId: string): Promise<DownloadResult> {
  const response = await fetch(buildApiUrl(API_BASE_URL, `/tasks/${taskId}/package/download`));
  if (!response.ok) {
    throw new Error(await extractApiError(response, "下载 Package"));
  }
  return {
    blob: await response.blob(),
    sha256: response.headers.get("x-sha256"),
  };
}
