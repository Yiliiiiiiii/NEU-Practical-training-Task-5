import type {
  AuditLogListResponse,
  CatalogResponse,
  ChunksReport,
  ContentOrganizationReport,
  DocumentImportResponse,
  KnowledgeCandidateListResponse,
  KnowledgeLoopApiResponse,
  KnowledgeMetrics,
  KnowledgePackListResponse,
  MappingReport,
  MappingTemplate,
  PackageMetadata,
  PackageManifest,
  ReviewListResponse,
  TargetSchema,
  TaskCreateResponse,
  TaskDetailResponse,
  TaskExecuteResponse,
  ValidationReport,
  VerifierReport
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

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
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listSchemas: () => request<CatalogResponse<TargetSchema>>("/api/v1/schemas"),
  listTemplates: () => request<CatalogResponse<MappingTemplate>>("/api/v1/templates"),
  importDocument: (uir: unknown) =>
    request<DocumentImportResponse>("/api/v1/documents/import", {
      method: "POST",
      body: JSON.stringify({ uir })
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
  getPackage: (taskId: string) =>
    request<PackageMetadata>(`/api/v1/tasks/${taskId}/package`),
  getKnowledgeLoopReport: () =>
    request<KnowledgeLoopApiResponse>(
      "/api/v1/evaluation-reports/real-world-knowledge-loop"
    ),
  listReviews: (status = "pending") =>
    request<ReviewListResponse>(`/api/v1/reviews?status=${encodeURIComponent(status)}`),
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
  listAuditLogs: (entityId?: string) =>
    request<AuditLogListResponse>(
      `/api/v1/audit-logs${entityId ? `?entity_id=${encodeURIComponent(entityId)}` : ""}`
    ),
  packageDownloadUrl: (taskId: string) => `${API_BASE}/api/v1/tasks/${taskId}/package/download`
};
