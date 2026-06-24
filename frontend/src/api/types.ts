export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export interface JsonObject {
  [key: string]: JsonValue;
}

export interface DocumentImportResponse {
  doc_id: string;
  status: string;
  block_count: number;
}

export interface DocumentListItem {
  doc_id: string;
  title: string | null;
  block_count: number;
}

export interface DocumentListResponse {
  items: DocumentListItem[];
  total: number;
}

export interface SchemaListItem {
  schema_id: string;
  name: string;
  version: string;
  fields_count: number;
}

export interface SchemaListResponse {
  items: SchemaListItem[];
}

export interface TargetField {
  field_id: string;
  name: string;
  display_name: string;
  type: string;
  required: boolean;
  aliases: string[];
  constraints: JsonObject;
}

export interface TargetSchema {
  schema_id: string;
  name: string;
  version: string;
  description?: string | null;
  fields: TargetField[];
  json_schema: JsonObject;
}

export interface TemplateListItem {
  template_id: string;
  schema_id: string;
  name: string;
  version: string;
  aliases_count: number;
  rules_count: number;
}

export interface TemplateListResponse {
  items: TemplateListItem[];
}

export interface MappingTemplate {
  template_id: string;
  schema_id: string;
  name: string;
  version: string;
  aliases: JsonObject;
  regex_rules: JsonObject[];
  transform_rules: JsonObject[];
  defaults: JsonObject;
  enum_maps: JsonObject;
}

export interface TaskCreateResponse {
  task_id: string;
  status: string;
}

export interface TaskListItem {
  task_id: string;
  doc_id: string;
  schema_id: string;
  template_id: string;
  status: string;
}

export interface TaskListResponse {
  items: TaskListItem[];
  total: number;
}

export interface TaskDetailResponse extends TaskListItem {
  schema_version: string;
  template_version: string;
  input_hash: string;
  options: JsonObject;
}

export interface GenerateCandidatesResponse {
  task_id: string;
  candidate_count: number;
  status: string;
}

export interface CandidateListItem {
  candidate_id: string;
  task_id: string;
  doc_id: string;
  source_path: string;
  source_name: string;
  display_name: string | null;
  value_sample: JsonValue | null;
  inferred_type: string;
  source_blocks: string[];
  confidence: number;
  evidence: string[];
}

export interface CandidateListResponse {
  items: CandidateListItem[];
}

export interface MappingRunResponse {
  task_id: string;
  mapped_count: number;
  review_required_count: number;
  status: string;
}

export interface MappingListItem {
  mapping_id: string;
  task_id: string;
  candidate_id: string;
  source_name: string;
  source_path: string;
  target_field_id: string;
  target_field_name: string;
  method: string;
  confidence: number;
  status: string;
  need_review: boolean;
  evidence: string[];
}

export interface MappingListResponse {
  items: MappingListItem[];
}

export interface ConvertResponse {
  task_id: string;
  status: string;
  outputs: string[];
}

export interface PackageResponse {
  package_id: string;
  status: string;
  zip_path: string;
  sha256: string | null;
}

export interface ReportResponse {
  [key: string]: JsonValue;
}

export interface DownloadResult {
  blob: Blob;
  sha256: string | null;
}

export type LearningCandidateType =
  | "alias_candidate"
  | "regex_candidate"
  | "enum_map_candidate"
  | "default_candidate"
  | "transform_candidate"
  | "gold_mapping_candidate"
  | "badcase_candidate";

export interface RealRunItem {
  real_run_id: string;
  task_id: string;
  doc_id: string;
  schema_id: string;
  template_id: string;
  input_hash: string;
  status: string;
  summary: JsonObject;
  report_paths: JsonObject;
}

export interface LearningCandidateItem {
  candidate_id: string;
  real_run_id: string;
  task_id: string;
  candidate_type: LearningCandidateType;
  status: "pending" | "approved" | "rejected" | "superseded";
  risk_level: "low" | "medium" | "high";
  target_field_id: string | null;
  proposed_payload: JsonObject;
  final_payload: JsonObject;
  evidence: JsonObject;
  generator: string;
  confidence: number;
}

export interface LearningCandidateListResponse {
  items: LearningCandidateItem[];
}

export interface CandidateDecisionPayload {
  decision: "approved" | "rejected";
  reviewer: string;
  final_payload?: JsonObject;
  reason: string;
}

export interface KnowledgePackItem {
  pack_id: string;
  name: string;
  scope: JsonObject;
  status: "draft" | "active" | "superseded";
  version: string;
  item_count: number;
  regression_report_path: string | null;
  reviewer: string;
}

export interface KnowledgePackCreatePayload {
  name: string;
  scope: JsonObject;
  candidate_ids: string[];
  reviewer: string;
}

export interface KnowledgePackListResponse {
  items: KnowledgePackItem[];
}

export interface KnowledgeMetricsResponse {
  real_runs: number;
  pending_candidates: number;
  approved_candidates: number;
  rejected_candidates: number;
  active_packs: number;
}
