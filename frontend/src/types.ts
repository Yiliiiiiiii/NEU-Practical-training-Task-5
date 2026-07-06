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

export type ExternalUirTraceItem = {
  external_path: string;
  canonical_path: string;
  strategy: string;
  confidence: number;
  evidence: string[];
  review_required: boolean;
  warning?: string | null;
};

export type ExternalUirSuggestion = {
  external_path: string;
  target_uir_location: string;
  operation: string;
  confidence: number;
  evidence: string;
  review_required: boolean;
  reason: string;
};

export type ExternalUirAdapterReport = {
  adapter_id: string;
  adapter_version: string;
  source_system: string;
  external_doc_id: string | null;
  generated_doc_id: string;
  status: string;
  dialect?: string | null;
  detected_dialect?: string | null;
  trace_coverage: number;
  block_count: number;
  table_count: number;
  warning_count: number;
  error_count: number;
  trace_items: ExternalUirTraceItem[];
  assisted_suggestions: ExternalUirSuggestion[];
  llm_used: boolean;
  llm_auto_accepted_count: number;
  warnings: string[];
  errors: string[];
  raw_payload_hash: string;
};

export type ExternalUirRouteEvidence = {
  evidence_type: "keyword" | "field_hint" | "metadata" | "table_label" | "adapter_hint";
  value: string;
  source_path?: string | null;
  weight: number;
  matched_schema: string;
};

export type ExternalUirRouteCandidate = {
  schema_id: string;
  template_id: string;
  confidence: number;
  reasons: string[];
  evidence: ExternalUirRouteEvidence[];
  risk_flags: string[];
};

export type ExternalUirRouteReport = {
  selected_schema_id: string | null;
  selected_template_id: string | null;
  confidence: number;
  reason: string;
  alternatives: Array<Record<string, any>>;
  review_required: boolean;
  candidates: ExternalUirRouteCandidate[];
  decision_reason: string;
  route_version: string;
};

export type ExternalUirConvertResponse = {
  standard_uir: Record<string, any>;
  adapter_report: ExternalUirAdapterReport;
  route_report: ExternalUirRouteReport | null;
  warnings: string[];
  errors: string[];
};

export type ExternalUirImportResponse = {
  doc_id: string;
  document: {
    doc_id: string;
    title: string | null;
    block_count: number;
  };
  adapter_report: ExternalUirAdapterReport;
  route_report: ExternalUirRouteReport | null;
  warnings: string[];
};

export type ExternalUirCreateTaskResponse = {
  task_id: string;
  status: string;
  review_required: boolean;
  warnings: string[];
};

export type SchemaDraftFieldCandidate = {
  field_name: string;
  source_labels: string[];
  value_examples: string[];
  frequency: number;
  inferred_type: string;
  evidence_paths: string[];
  risk_flags: string[];
  confidence: number;
  review_required: boolean;
};

export type SchemaDraftDiscovery = {
  sample_count: number;
  field_candidates: SchemaDraftFieldCandidate[];
  warnings: string[];
  llm_auto_accepted_count: number;
};

export type SchemaDraftRiskReport = {
  must_not_auto_activate: boolean;
  risk_count: number;
  risks: Array<{
    risk_type: string;
    source_label?: string | null;
    target_field?: string | null;
    severity: string;
    action: string;
  }>;
  badcase_violations: number;
  llm_auto_accepted_count: number;
};

export type SchemaDraftPackage = {
  draft_id: string;
  created_at: string;
  status: "draft";
  discovery: SchemaDraftDiscovery;
  draft_schema: {
    schema_id: string;
    name: string;
    version: string;
    status: "draft";
    fields: Array<Record<string, any>>;
    must_not_auto_activate: boolean;
  };
  draft_template: {
    template_id: string;
    schema_id: string;
    name: string;
    version: string;
    status: "draft";
    alias_rules: Array<Record<string, any>>;
    regex_suggestions: Array<Record<string, any>>;
    must_not_auto_activate: boolean;
  };
  risk_report: SchemaDraftRiskReport;
  draft_report: {
    sample_count: number;
    candidate_count: number;
    source_doc_ids: string[];
    deterministic: boolean;
    must_not_auto_activate: boolean;
    risk_count: number;
    badcase_violations: number;
    llm_auto_accepted_count: number;
    secret_leak_count: number;
  };
  must_not_auto_activate: boolean;
};

export type SchemaDraftExportResponse = {
  draft_id: string;
  files: Record<string, string>;
  sha256: Record<string, string>;
  must_not_auto_activate: boolean;
};

export type ExternalUirAdapterCapability = {
  adapter_id: string;
  adapter_version: string;
  supported_dialects: string[];
  source_systems: string[];
  supports_tables: boolean;
  supports_sections: boolean;
  supports_pages: boolean;
  supports_bbox: boolean;
  requires_llm: boolean;
  description: string;
};

export type ExternalUirAdapterListResponse = {
  items: ExternalUirAdapterCapability[];
};

export type ExternalUirAdapterSelectionItem = {
  adapter_id: string;
  confidence: number;
};

export type ExternalUirAdapterDetectResponse = {
  selected_adapter: ExternalUirAdapterSelectionItem | null;
  alternatives: ExternalUirAdapterSelectionItem[];
  review_required: boolean;
  error?: string | null;
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

export type LineageNodeType =
  | "external_field"
  | "adapter_trace"
  | "uir_block"
  | "field_candidate"
  | "mapping_decision"
  | "review_decision"
  | "knowledge_pack"
  | "schema_field"
  | "canonical_field"
  | "rendered_artifact"
  | "chunk"
  | "package_manifest_entry"
  | "consumer_contract";

export type LineageStatus =
  | "accepted"
  | "review_required"
  | "blocked"
  | "failed"
  | "warning"
  | "informational";

export type LineageNode = {
  node_id: string;
  node_type: LineageNodeType;
  label: string;
  status: LineageStatus;
  doc_id?: string | null;
  task_id?: string | null;
  schema_id?: string | null;
  schema_version?: string | null;
  template_id?: string | null;
  template_version?: string | null;
  field_name?: string | null;
  block_id?: string | null;
  chunk_id?: string | null;
  artifact_path?: string | null;
  confidence?: number | null;
  confidence_tier?: string | null;
  risk_flags: string[];
  review_required_reason?: string | null;
  metadata: Record<string, any>;
};

export type LineageEdge = {
  edge_id: string;
  source_node_id: string;
  target_node_id: string;
  edge_type: string;
  confidence?: number | null;
  evidence_ids: string[];
  metadata: Record<string, any>;
};

export type LineageEvidence = {
  evidence_id: string;
  evidence_type: string;
  text?: string | null;
  path?: string | null;
  block_id?: string | null;
  artifact_path?: string | null;
  sha256?: string | null;
  metadata: Record<string, any>;
};

export type LineageSummary = {
  node_count: number;
  edge_count: number;
  field_count: number;
  fields_traced: number;
  field_lineage_coverage: number;
  chunk_count: number;
  chunks_traced: number;
  chunk_lineage_coverage: number;
  artifact_count: number;
  artifacts_traced: number;
  artifact_lineage_coverage: number;
  review_required_count: number;
  badcase_blocked_count: number;
  knowledge_influenced_count: number;
  lineage_coverage: number;
  source_mode: string;
  [key: string]: unknown;
};

export type LineageGraph = {
  graph_id: string;
  doc_id: string;
  task_id?: string | null;
  package_id?: string | null;
  schema_id?: string | null;
  template_id?: string | null;
  generated_at: string;
  lineage_version: string;
  nodes: LineageNode[];
  edges: LineageEdge[];
  evidence: LineageEvidence[];
  summary: Record<string, any>;
  warnings: string[];
};

export type LineageQueryResult = {
  root_node_id: string;
  direction: "upstream" | "downstream" | "both";
  max_depth: number;
  nodes: LineageNode[];
  edges: LineageEdge[];
  evidence: LineageEvidence[];
  summary: Record<string, any>;
};

export type ValidationReport = {
  task_id: string;
  schema_id: string;
  passed: boolean;
  summary: Record<string, unknown>;
  issues: Array<Record<string, any>>;
};

export type ValidationIssue = Record<string, any> & {
  level?: string;
  severity?: string;
  message?: string;
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

export type ManifestFile = {
  path: string;
  size_bytes: number;
  sha256: string;
  role?: string | null;
};

export type PackageManifest = {
  manifest_version: string;
  package_id: string;
  package_version: string;
  task_id: string;
  doc_id: string;
  created_at: string;
  files: ManifestFile[];
  generator: Record<string, string>;
};

export type VerifierReport = {
  passed: boolean;
  checks?: Array<Record<string, any>>;
  errors: string[];
  warnings: string[];
};

export type KnowledgeLoopReport = {
  approved_candidates: number;
  rejected_candidates: number;
  badcase_violation_count: number;
  old_snapshot_unchanged: boolean;
  before: {
    auto_mapped_fields: number;
    review_required_count: number;
    missing_required_count: number;
  };
  after: {
    auto_mapped_fields: number;
    review_required_count: number;
    missing_required_count: number;
  };
  activated_aliases: Record<string, string[]>;
  decision_evidence: Array<Record<string, any>>;
};

export type KnowledgeLoopApiResponse =
  | {
      status: "available";
      report: KnowledgeLoopReport;
      recommended_command?: string | null;
    }
  | {
      status: "unavailable";
      report?: null;
      recommended_command: string;
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

export type ReviewWorkbenchSummary = {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  resolution_rate: number;
  negative_rule_count: number;
};

export type ReviewImpactPreview = {
  review_id: string;
  would_affect: Array<{
    review_id: string;
    doc_id: string | null;
    source_label: string;
    target_field: string;
    confidence_after: number;
  }>;
  risk_flags: string[];
  badcase_hits: string[];
};

export type ReviewGroupedResponse = {
  group_by: string;
  items: Array<{ key: string; count: number; review_ids: string[] }>;
};

export type KnowledgeConflictResponse = {
  total: number;
  items: Array<{
    conflict_type: string;
    source_label: string;
    targets: string[];
    pack_ids: string[];
    severity: string;
  }>;
};

export type EvaluationDataset = {
  dataset_id: string;
  dataset_type: string;
  doc_count: number;
  doc_types: Record<string, number>;
  gold_files: string[];
};

export type EvaluationMetricDefinition = {
  metric_id: string;
  description: string;
  higher_is_better: boolean;
  threshold?: number | boolean | null;
  gate_op?: string | null;
};

export type EvaluationGateResult = {
  metric: string;
  op: string;
  expected: number | boolean;
  actual?: number | boolean | null;
  passed: boolean;
  reason?: string | null;
};

export type EvaluationRun = {
  run_id: string;
  created_at: string;
  git_commit: string;
  dataset_id: string;
  eval_type: string;
  metrics: Record<string, any>;
  passed: boolean;
  failed_gates: EvaluationGateResult[];
  report_paths: Record<string, string>;
};

export type EvaluationScorecard = {
  run_count: number;
  metrics: Record<string, any>;
  passed: boolean;
  failed_gates: EvaluationGateResult[];
  summary: {
    status: "passed" | "needs_attention" | "failed";
    generated_at: string;
    gates_passed: number;
    gates_total: number;
  };
  cards: Array<{
    metric_id: string;
    name: string;
    value?: number | boolean | string | null;
    target: number | boolean;
    status: "passed" | "needs_attention" | "failed";
    explanation: string;
  }>;
  warnings: string[];
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
