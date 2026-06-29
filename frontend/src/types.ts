export type TargetField = {
  field_id: string;
  name: string;
  display_name: string;
  type: string;
  required: boolean;
  aliases: string[];
};

export type CatalogStatus = "draft" | "active" | "archived" | string;

export type TargetSchema = {
  schema_id: string;
  name: string;
  version: string;
  description?: string | null;
  fields?: TargetField[];
  status?: CatalogStatus;
  content_hash?: string;
};

export type MappingTemplate = {
  template_id: string;
  schema_id: string;
  name: string;
  version: string;
  aliases?: Record<string, string[]>;
  status?: CatalogStatus;
  content_hash?: string;
};

export type CatalogResponse<T> = {
  items: T[];
  total: number;
};

export type DocumentImportResponse = {
  doc_id: string;
  status: string;
  block_count: number;
};

export type TaskCreateResponse = {
  task_id: string;
  status: string;
};

export type TaskExecuteResponse = {
  task_id: string;
  status: string;
  report_paths: Record<string, string>;
  package_zip_path: string | null;
  review_required_count: number;
  unmapped_required_count: number;
};

export type TaskDetailResponse = {
  task_id: string;
  status: string;
  doc_id: string;
  schema_id: string;
  schema_version: string;
  template_id: string;
  template_version: string;
  input_hash: string;
  options: Record<string, unknown>;
  report_paths: Record<string, string>;
  package_zip_path: string | null;
};

export type ContentOrganizationOptions = {
  chunk_strategy:
    | "fixed_window"
    | "heading_aware"
    | "source_block_aware"
    | "table_protect"
    | "parent_child";
  target_tokens: number;
  min_tokens: number;
  max_tokens: number;
  overlap_tokens: number;
  protect_tables: boolean;
  protect_lists: boolean;
  protect_code_blocks: boolean;
  enable_parent_child: boolean;
  enable_light_semantic_boundary: boolean;
  summary_mode: "none" | "deterministic";
  keyword_mode: "none" | "deterministic";
};

export type MappingReport = {
  task_id: string;
  schema_id: string;
  summary: Record<string, unknown>;
  mappings: Array<Record<string, any>>;
  unmapped: Array<Record<string, any>>;
  review_required_items: Array<Record<string, any>>;
};

export type ValidationReport = {
  task_id: string;
  schema_id: string;
  passed: boolean;
  summary: Record<string, unknown>;
  issues: Array<Record<string, any>>;
};

export type ContentOrganizationReport = {
  task_id: string;
  doc_id: string;
  chunk_count: number;
  chunks_with_summary: number;
  chunks_with_keywords: number;
  chunks_with_source_links: number;
  chunks_with_content_tags: number;
  chunks_with_quality_tags: number;
  warnings: string[];
  summary: Record<string, any>;
};

export type ChunkPreview = {
  chunk_id: string;
  parent_chunk_id?: string | null;
  strategy?: string | null;
  granularity?: "parent" | "child" | null;
  title?: string | null;
  title_path?: string[];
  token_estimate?: number;
  char_count?: number;
  text: string;
  summary?: string;
  keywords?: string[];
  content_tags?: string[];
  management_tags?: string[];
  quality_tags?: string[];
  quality_flags?: string[];
  tags?: {
    content?: string[];
    management?: string[];
    quality?: string[];
  };
  source_block_ids?: string[];
  source_links?: Array<Record<string, unknown>>;
};

export type ChunksReport = {
  items: ChunkPreview[];
  total: number;
};

export type PackageMetadata = {
  package_id: string;
  task_id: string;
  doc_id: string;
  schema_id: string;
  template_id: string;
  package_version: string;
  zip_path: string;
  status: string;
  sha256: string | null;
  created_at: string;
};

export type ReviewRecord = {
  review_id: string;
  task_id: string;
  doc_id: string | null;
  schema_id: string | null;
  template_id: string | null;
  source_field_name: string | null;
  source_path: string | null;
  target_field_id: string | null;
  suggested_by: string | null;
  confidence: number | null;
  reason: string | null;
  status: string;
  reviewer: string;
  review_comment: string | null;
  created_at: string;
  updated_at: string;
};

export type ReviewListResponse = {
  items: ReviewRecord[];
  total: number;
};

export type KnowledgeCandidate = {
  candidate_id: string;
  review_id: string;
  schema_id: string;
  template_id: string;
  target_field_id: string;
  alias: string;
  candidate_type: string;
  support_count: number;
  badcase_hit: boolean;
  status: string;
  created_at: string;
  updated_at: string;
};

export type KnowledgeCandidateListResponse = {
  items: KnowledgeCandidate[];
  total: number;
};

export type KnowledgePack = {
  pack_id: string;
  name: string;
  schema_id: string;
  template_id: string;
  version: string;
  status: string;
  created_by: string;
  metadata: Record<string, unknown>;
  items: Array<Record<string, any>>;
  created_at: string;
  activated_at: string | null;
  updated_at: string;
};

export type KnowledgePackListResponse = {
  items: KnowledgePack[];
  total: number;
};

export type KnowledgeMetrics = {
  pending_reviews: number;
  approved_reviews: number;
  rejected_reviews: number;
  pending_candidates: number;
  accepted_candidates: number;
  rejected_candidates: number;
  blocked_candidates: number;
  draft_packs: number;
  active_packs: number;
  archived_packs: number;
};

export type AuditLog = {
  audit_id: string;
  created_at: string;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  method: string | null;
  path: string | null;
  status_code: number | null;
  success: boolean;
  metadata: Record<string, unknown>;
};

export type AuditLogListResponse = {
  items: AuditLog[];
  total: number;
};
