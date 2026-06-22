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
