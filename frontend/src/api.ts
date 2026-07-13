import type {
  AuditLogListResponse,
  CatalogResponse,
  ChunksReport,
  ContentOrganizationReport,
  DocumentImportResponse,
  EvaluationDataset,
  EvaluationMetricDefinition,
  EvaluationRun,
  EvaluationScorecard,
  ExternalUirAdapterDetectResponse,
  ExternalUirAdapterReport,
  ExternalUirAdapterListResponse,
  ExternalUirConvertResponse,
  ExternalUirCreateTaskResponse,
  ExternalUirImportResponse,
  ExternalUirRouteReport,
  KnowledgeCandidateListResponse,
  KnowledgeConflictResponse,
  KnowledgeLoopApiResponse,
  KnowledgeMetrics,
  KnowledgePackListResponse,
  LineageGraph,
  LineageQueryResult,
  LineageSummary,
  MappingReport,
  MappingTemplate,
  PackageMetadata,
  PackageManifest,
  ReviewListResponse,
  ReviewGroupedResponse,
  ReviewImpactPreview,
  ReviewWorkbenchSummary,
  SchemaDraftDiscovery,
  SchemaDraftExportResponse,
  SchemaDraftPackage,
  TargetSchema,
  TaskCreateResponse,
  TaskDetailResponse,
  TaskExecuteResponse,
  TaskListResponse,
  ValidationReport,
  VerifierReport
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export class ApiRequestError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiRequestError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : message;
    } catch {
      // Keep the HTTP status text.
    }
    throw new ApiRequestError(message, response.status);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  listSchemas: () => request<CatalogResponse<TargetSchema>>("/api/v1/schemas"),
  listTemplates: () => request<CatalogResponse<MappingTemplate>>("/api/v1/templates"),
  listExternalUirAdapters: () =>
    request<ExternalUirAdapterListResponse>("/api/v1/external-uir/adapters"),
  detectExternalUirAdapter: (payload: {
    payload: Record<string, unknown>;
    source_system: string;
    dialect_hint?: string | null;
  }) =>
    request<ExternalUirAdapterDetectResponse>("/api/v1/external-uir/detect", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  discoverSchemaDraftFields: (documents: Array<Record<string, any>>) =>
    request<SchemaDraftDiscovery>("/api/v1/schema-drafts/discover", {
      method: "POST",
      body: JSON.stringify({ documents })
    }),
  generateSchemaDraft: (payload: {
    documents: Array<Record<string, any>>;
    schema_id: string;
    schema_name: string;
    template_id: string;
  }) =>
    request<SchemaDraftPackage>("/api/v1/schema-drafts/generate", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  getSchemaDraft: (draftId: string) =>
    request<SchemaDraftPackage>(`/api/v1/schema-drafts/${draftId}`),
  validateSchemaDraft: (draftId: string) =>
    request<SchemaDraftPackage["risk_report"]>(
      `/api/v1/schema-drafts/${draftId}/validate`,
      { method: "POST" }
    ),
  exportSchemaDraft: (draftId: string) =>
    request<SchemaDraftExportResponse>(`/api/v1/schema-drafts/${draftId}/export`, {
      method: "POST"
    }),
  importDocument: (uir: unknown) =>
    request<DocumentImportResponse>("/api/v1/documents/import", {
      method: "POST",
      body: JSON.stringify({ uir })
    }),
  convertExternalUir: (payload: {
    payload: Record<string, unknown>;
    source_system: string;
    dialect_hint?: string | null;
    route_schema: boolean;
    allow_llm: boolean;
    llm_mode?: string | null;
  }) =>
    request<ExternalUirConvertResponse>("/api/v1/external-uir/convert", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  importExternalUir: (payload: {
    payload: Record<string, unknown>;
    source_system: string;
    dialect_hint?: string | null;
    route_schema: boolean;
    allow_llm: boolean;
    llm_mode?: string | null;
  }) =>
    request<ExternalUirImportResponse>("/api/v1/external-uir/import", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  createExternalUirTask: (payload: {
    doc_id: string;
    schema_id: string;
    template_id: string;
    schema_version?: string;
    template_version?: string;
    options?: Record<string, unknown>;
    route_report?: ExternalUirRouteReport | null;
    adapter_report?: ExternalUirAdapterReport | null;
  }) =>
    request<ExternalUirCreateTaskResponse>("/api/v1/external-uir/create-task", {
      method: "POST",
      body: JSON.stringify({
        schema_version: "1.0.0",
        template_version: "1.0.0",
        options: {},
        ...payload
      })
    }),
  createTask: (payload: {
    doc_id: string;
    schema_id: string;
    template_id: string;
    options?: Record<string, unknown>;
  }) =>
    request<TaskCreateResponse>("/api/v1/tasks", {
      method: "POST",
      body: JSON.stringify({
        schema_version: "1.0.0",
        template_version: "1.0.0",
        options: { enable_llm_fallback: false, ...(payload.options ?? {}) },
        ...payload
      })
    }),
  listTasks: (page = 1, pageSize = 100) =>
    request<TaskListResponse>(`/api/v1/tasks?page=${page}&page_size=${pageSize}`),
  executeTask: (taskId: string) =>
    request<TaskExecuteResponse>(`/api/v1/tasks/${taskId}/execute`, {
      method: "POST"
    }),
  getTask: (taskId: string) => request<TaskDetailResponse>(`/api/v1/tasks/${taskId}`),
  getMappingReport: (taskId: string) =>
    request<MappingReport>(`/api/v1/tasks/${taskId}/reports/mapping`),
  getValidationReport: (taskId: string) =>
    request<ValidationReport>(`/api/v1/tasks/${taskId}/reports/validation`),
  getContentOrganizationReport: (taskId: string) =>
    request<ContentOrganizationReport>(
      `/api/v1/tasks/${taskId}/reports/content-organization`
    ),
  getChunksReport: (taskId: string) =>
    request<ChunksReport>(`/api/v1/tasks/${taskId}/reports/chunks`),
  getManifestReport: (taskId: string) =>
    request<PackageManifest>(`/api/v1/tasks/${taskId}/reports/manifest`),
  getVerifierReport: (taskId: string) =>
    request<VerifierReport>(`/api/v1/tasks/${taskId}/reports/verifier`),
  getLineage: (taskId: string) =>
    request<LineageGraph>(`/api/v1/tasks/${taskId}/lineage`),
  getLineageSummary: (taskId: string) =>
    request<LineageSummary>(`/api/v1/tasks/${taskId}/lineage/summary`),
  getFieldLineage: (
    taskId: string,
    fieldName: string,
    direction = "upstream",
    maxDepth = 8
  ) =>
    request<LineageQueryResult>(
      `/api/v1/tasks/${taskId}/lineage/fields/${encodeURIComponent(fieldName)}?direction=${direction}&max_depth=${maxDepth}`
    ),
  getChunkLineage: (
    taskId: string,
    chunkId: string,
    direction = "upstream",
    maxDepth = 8
  ) =>
    request<LineageQueryResult>(
      `/api/v1/tasks/${taskId}/lineage/chunks/${encodeURIComponent(chunkId)}?direction=${direction}&max_depth=${maxDepth}`
    ),
  getArtifactLineage: (
    taskId: string,
    artifactPath: string,
    direction = "both",
    maxDepth = 8
  ) =>
    request<LineageQueryResult>(
      `/api/v1/tasks/${taskId}/lineage/artifacts/${encodeURIComponent(artifactPath)}?direction=${direction}&max_depth=${maxDepth}`
    ),
  getPackage: (taskId: string) =>
    request<PackageMetadata>(`/api/v1/tasks/${taskId}/package`),
  getKnowledgeLoopReport: () =>
    request<KnowledgeLoopApiResponse>(
      "/api/v1/evaluation-reports/real-world-knowledge-loop"
    ),
  listReviews: (status = "pending") =>
    request<ReviewListResponse>(`/api/v1/reviews?status=${encodeURIComponent(status)}`),
  getReviewSummary: () =>
    request<ReviewWorkbenchSummary>("/api/v1/reviews/summary"),
  getGroupedReviews: (groupBy: string) =>
    request<ReviewGroupedResponse>(
      `/api/v1/reviews/grouped?group_by=${encodeURIComponent(groupBy)}`
    ),
  getReviewImpact: (reviewId: string) =>
    request<ReviewImpactPreview>(`/api/v1/reviews/${reviewId}/impact-preview`, {
      method: "POST"
    }),
  batchApproveReviews: (reviewIds: string[]) =>
    request("/api/v1/reviews/batch-approve", {
      method: "POST",
      body: JSON.stringify({
        review_ids: reviewIds,
        reviewer: "demo_user",
        comment: "Approved in Review Workbench"
      })
    }),
  batchRejectReviews: (reviewIds: string[]) =>
    request("/api/v1/reviews/batch-reject", {
      method: "POST",
      body: JSON.stringify({
        review_ids: reviewIds,
        reviewer: "demo_user",
        comment: "Rejected in Review Workbench"
      })
    }),
  approveReview: (reviewId: string, createKnowledgeCandidate = true) =>
    request(`/api/v1/reviews/${reviewId}/approve`, {
      method: "POST",
      body: JSON.stringify({
        reviewer: "demo_user",
        comment: "在工作台中通过",
        create_knowledge_candidate: createKnowledgeCandidate
      })
    }),
  rejectReview: (reviewId: string) =>
    request(`/api/v1/reviews/${reviewId}/reject`, {
      method: "POST",
      body: JSON.stringify({
        reviewer: "demo_user",
        comment: "在工作台中拒绝"
      })
    }),
  listKnowledgeCandidates: () =>
    request<KnowledgeCandidateListResponse>("/api/v1/knowledge/candidates"),
  acceptKnowledgeCandidate: (candidateId: string) =>
    request(`/api/v1/knowledge/candidates/${candidateId}/accept`, { method: "POST" }),
  listKnowledgePacks: () => request<KnowledgePackListResponse>("/api/v1/knowledge/packs"),
  createKnowledgePack: (schemaId: string, templateId: string) =>
    request("/api/v1/knowledge/packs", {
      method: "POST",
      body: JSON.stringify({
        schema_id: schemaId,
        template_id: templateId,
        name: `${schemaId} Review 别名规则`,
        created_by: "demo_user"
      })
    }),
  activateKnowledgePack: (packId: string) =>
    request(`/api/v1/knowledge/packs/${packId}/activate`, { method: "POST" }),
  getKnowledgeMetrics: () => request<KnowledgeMetrics>("/api/v1/knowledge/metrics"),
  getKnowledgeConflicts: () =>
    request<KnowledgeConflictResponse>("/api/v1/knowledge/conflicts"),
  listEvaluationDatasets: () =>
    request<{ items: EvaluationDataset[] }>("/api/v1/evaluation-center/datasets"),
  listEvaluationMetrics: () =>
    request<{ items: EvaluationMetricDefinition[] }>("/api/v1/evaluation-center/metrics"),
  listEvaluationRuns: () =>
    request<{ items: EvaluationRun[]; total: number }>("/api/v1/evaluation-center/runs"),
  getEvaluationScorecard: () =>
    request<EvaluationScorecard>("/api/v1/evaluation-center/scorecard"),
  evaluationReportUrl: (runId: string, reportKey: string) =>
    `${API_BASE}/api/v1/evaluation-center/runs/${encodeURIComponent(runId)}/reports/${encodeURIComponent(reportKey)}`,
  registerEvaluationRun: (payload: {
    dataset_id: string;
    eval_type: string;
    git_commit?: string;
    metrics?: Record<string, any>;
    report_paths?: Record<string, string>;
  }) =>
    request<EvaluationRun>("/api/v1/evaluation-center/run", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  listAuditLogs: (entityId?: string, limit = 100, offset = 0) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (entityId) params.set("entity_id", entityId);
    return request<AuditLogListResponse>(`/api/v1/audit-logs?${params.toString()}`);
  },
  packageDownloadUrl: (taskId: string) => `${API_BASE}/api/v1/tasks/${taskId}/package/download`
};
