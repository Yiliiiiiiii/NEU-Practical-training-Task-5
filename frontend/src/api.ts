import type {
  CatalogResponse,
  ChunksReport,
  ContentOrganizationReport,
  DocumentImportResponse,
  KnowledgeCandidateListResponse,
  KnowledgeMetrics,
  KnowledgePackListResponse,
  MappingReport,
  MappingTemplate,
  PackageMetadata,
  ReviewListResponse,
  TargetSchema,
  TaskCreateResponse,
  TaskDetailResponse,
  TaskExecuteResponse,
  ValidationReport
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
  getPackage: (taskId: string) =>
    request<PackageMetadata>(`/api/v1/tasks/${taskId}/package`),
  listReviews: (status = "pending") =>
    request<ReviewListResponse>(`/api/v1/reviews?status=${encodeURIComponent(status)}`),
  approveReview: (reviewId: string, createKnowledgeCandidate = true) =>
    request(`/api/v1/reviews/${reviewId}/approve`, {
      method: "POST",
      body: JSON.stringify({
        reviewer: "demo_user",
        comment: "Approved in workbench",
        create_knowledge_candidate: createKnowledgeCandidate
      })
    }),
  rejectReview: (reviewId: string) =>
    request(`/api/v1/reviews/${reviewId}/reject`, {
      method: "POST",
      body: JSON.stringify({
        reviewer: "demo_user",
        comment: "Rejected in workbench"
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
        name: `${schemaId} review aliases`,
        created_by: "demo_user"
      })
    }),
  activateKnowledgePack: (packId: string) =>
    request(`/api/v1/knowledge/packs/${packId}/activate`, { method: "POST" }),
  getKnowledgeMetrics: () => request<KnowledgeMetrics>("/api/v1/knowledge/metrics"),
  packageDownloadUrl: (taskId: string) => `${API_BASE}/api/v1/tasks/${taskId}/package/download`
};
