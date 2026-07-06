import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ClipboardList,
  FileJson,
  GitBranch,
  Package,
  Play,
  RefreshCw,
  Tags,
  UploadCloud,
  Users
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";

import { api } from "./api";
import { ChunkEvidencePanel } from "./components/ChunkEvidencePanel";
import { DownstreamReadinessPanel } from "./components/DownstreamReadinessPanel";
import { EvaluationCenterPanel } from "./components/EvaluationCenterPanel";
import { ExternalUirPanel } from "./components/ExternalUirPanel";
import { KnowledgeComparisonPanel } from "./components/KnowledgeComparisonPanel";
import { LineagePanel } from "./components/LineagePanel";
import { MappingEvidencePanel } from "./components/MappingEvidencePanel";
import { PackageManifestPanel } from "./components/PackageManifestPanel";
import { ReviewWorkbenchPanel } from "./components/ReviewWorkbenchPanel";
import { SchemaDraftLabPanel } from "./components/SchemaDraftLabPanel";
import { ValidationIssuePanel } from "./components/ValidationIssuePanel";
import { sampleUirText } from "./sampleUir";
import type {
  AuditLog,
  ChunksReport,
  ContentOrganizationOptions,
  ContentOrganizationReport,
  ExternalUirImportResponse,
  ExternalUirRouteReport,
  KnowledgeCandidate,
  KnowledgeLoopApiResponse,
  KnowledgeMetrics,
  KnowledgePack,
  MappingReport,
  MappingTemplate,
  PackageManifest,
  PackageMetadata,
  ReviewRecord,
  TargetSchema,
  TaskCreateResponse,
  TaskDetailResponse,
  ValidationReport,
  VerifierReport
} from "./types";

type RunState = "idle" | "loading" | "ready" | "working" | "error";

const defaultContentOptions: ContentOrganizationOptions = {
  chunk_strategy: "heading_aware",
  target_tokens: 768,
  min_tokens: 128,
  max_tokens: 1024,
  overlap_tokens: 80,
  protect_tables: true,
  protect_lists: true,
  protect_code_blocks: true,
  enable_parent_child: false,
  enable_light_semantic_boundary: true,
  summary_mode: "deterministic",
  keyword_mode: "deterministic"
};

function App() {
  const [schemas, setSchemas] = useState<TargetSchema[]>([]);
  const [templates, setTemplates] = useState<MappingTemplate[]>([]);
  const [selectedSchema, setSelectedSchema] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [uirText, setUirText] = useState(sampleUirText);
  const [docId, setDocId] = useState("");
  const [taskId, setTaskId] = useState("");
  const [task, setTask] = useState<TaskDetailResponse | null>(null);
  const [mapping, setMapping] = useState<MappingReport | null>(null);
  const [validation, setValidation] = useState<ValidationReport | null>(null);
  const [contentOrg, setContentOrg] = useState<ContentOrganizationReport | null>(null);
  const [chunks, setChunks] = useState<ChunksReport | null>(null);
  const [pkg, setPkg] = useState<PackageMetadata | null>(null);
  const [manifest, setManifest] = useState<PackageManifest | null>(null);
  const [verifier, setVerifier] = useState<VerifierReport | null>(null);
  const [knowledgeLoop, setKnowledgeLoop] = useState<KnowledgeLoopApiResponse | null>(null);
  const [reviews, setReviews] = useState<ReviewRecord[]>([]);
  const [knowledgeCandidates, setKnowledgeCandidates] = useState<KnowledgeCandidate[]>([]);
  const [knowledgePacks, setKnowledgePacks] = useState<KnowledgePack[]>([]);
  const [knowledgeMetrics, setKnowledgeMetrics] = useState<KnowledgeMetrics | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [contentOptions, setContentOptions] =
    useState<ContentOrganizationOptions>(defaultContentOptions);
  const [runState, setRunState] = useState<RunState>("idle");
  const [error, setError] = useState("");

  useEffect(() => {
    void loadCatalog();
  }, []);

  const templateOptions = useMemo(
    () => templates.filter((template) => template.schema_id === selectedSchema),
    [templates, selectedSchema]
  );

  const selectedSchemaModel = schemas.find((schema) => schema.schema_id === selectedSchema);

  async function loadCatalog() {
    setRunState("loading");
    setError("");
    try {
      const [schemaCatalog, templateCatalog] = await Promise.all([
        api.listSchemas(),
        api.listTemplates()
      ]);
      setSchemas(schemaCatalog.items);
      setTemplates(templateCatalog.items);
      const defaultSchema =
        schemaCatalog.items.find((schema) => schema.schema_id === "policy_doc") ??
        schemaCatalog.items[0];
      setSelectedSchema(defaultSchema?.schema_id ?? "");
      const defaultTemplate =
        templateCatalog.items.find((template) => template.template_id === "policy_doc_base_v1") ??
        templateCatalog.items.find((template) => template.schema_id === defaultSchema?.schema_id) ??
        templateCatalog.items[0];
      setSelectedTemplate(defaultTemplate?.template_id ?? "");
      setRunState("ready");
    } catch (caught) {
      setRunState("error");
      setError(errorMessage(caught));
    }
  }

  async function importDocument() {
    setRunState("working");
    setError("");
    try {
      const uir = JSON.parse(uirText);
      const imported = await api.importDocument(uir);
      setDocId(imported.doc_id);
      setTaskId("");
      setTask(null);
      setMapping(null);
      setValidation(null);
      setContentOrg(null);
      setChunks(null);
      setPkg(null);
      setManifest(null);
      setVerifier(null);
      setKnowledgeLoop(null);
      setAuditLogs([]);
      clearReviewKnowledge();
      setRunState("ready");
    } catch (caught) {
      setRunState("error");
      setError(errorMessage(caught));
    }
  }

  function resetTaskOutputs() {
    setTask(null);
    setMapping(null);
    setValidation(null);
    setContentOrg(null);
    setChunks(null);
    setPkg(null);
    setManifest(null);
    setVerifier(null);
    setKnowledgeLoop(null);
    setAuditLogs([]);
    clearReviewKnowledge();
  }

  function applyRecommendedRoute(route: ExternalUirRouteReport) {
    if (route.selected_schema_id) {
      setSelectedSchema(route.selected_schema_id);
    }
    if (route.selected_template_id) {
      setSelectedTemplate(route.selected_template_id);
    }
  }

  function handleExternalImport(response: ExternalUirImportResponse) {
    setDocId(response.doc_id);
    setTaskId("");
    resetTaskOutputs();
  }

  async function handleExternalTaskCreated(response: TaskCreateResponse) {
    setTaskId(response.task_id);
    const detail = await api.getTask(response.task_id);
    setTask(detail);
    setMapping(null);
    setValidation(null);
    setContentOrg(null);
    setChunks(null);
    setPkg(null);
    setManifest(null);
    setVerifier(null);
    setKnowledgeLoop(null);
    setAuditLogs([]);
    clearReviewKnowledge();
  }

  async function createTask() {
    if (!docId || !selectedSchema || !selectedTemplate) {
      setError("请先导入 Document，并选择 Schema 和 Template。");
      return;
    }
    setRunState("working");
    setError("");
    try {
      const created = await api.createTask({
        doc_id: docId,
        schema_id: selectedSchema,
        template_id: selectedTemplate,
        options: {
          content_organization: {
            ...contentOptions,
            enable_parent_child:
              contentOptions.enable_parent_child ||
              contentOptions.chunk_strategy === "parent_child"
          }
        }
      });
      setTaskId(created.task_id);
      const detail = await api.getTask(created.task_id);
      setTask(detail);
      setMapping(null);
      setValidation(null);
      setContentOrg(null);
      setChunks(null);
      setPkg(null);
      setManifest(null);
      setVerifier(null);
      setKnowledgeLoop(null);
      setAuditLogs([]);
      clearReviewKnowledge();
      setRunState("ready");
    } catch (caught) {
      setRunState("error");
      setError(errorMessage(caught));
    }
  }

  async function executeTask() {
    if (!taskId) {
      setError("请先创建 Task。");
      return;
    }
    setRunState("working");
    setError("");
    try {
      await api.executeTask(taskId);
      await refreshArtifacts(taskId);
      setRunState("ready");
    } catch (caught) {
      setRunState("error");
      setError(errorMessage(caught));
    }
  }

  async function refreshArtifacts(id = taskId) {
    if (!id) {
      return;
    }
    const [
      detail,
      mappingReport,
      validationReport,
      contentOrganizationReport,
      chunksReport,
      packageMetadata,
      manifestReport,
      verifierReport,
      knowledgeLoopReport
    ] = await Promise.all([
      api.getTask(id),
      api.getMappingReport(id),
      api.getValidationReport(id),
      api.getContentOrganizationReport(id),
      api.getChunksReport(id),
      api.getPackage(id),
      api.getManifestReport(id),
      api.getVerifierReport(id),
      api.getKnowledgeLoopReport()
    ]);
    setTask(detail);
    setMapping(mappingReport);
    setValidation(validationReport);
    setContentOrg(contentOrganizationReport);
    setChunks(chunksReport);
    setPkg(packageMetadata);
    setManifest(manifestReport);
    setVerifier(verifierReport);
    setKnowledgeLoop(knowledgeLoopReport);
    await refreshReviewKnowledge();
    await refreshAuditLogs(id);
  }

  async function refreshReviewKnowledge() {
    const [pendingReviews, candidates, packs, metrics] = await Promise.all([
      api.listReviews("pending"),
      api.listKnowledgeCandidates(),
      api.listKnowledgePacks(),
      api.getKnowledgeMetrics()
    ]);
    setReviews(pendingReviews.items);
    setKnowledgeCandidates(candidates.items);
    setKnowledgePacks(packs.items);
    setKnowledgeMetrics(metrics);
  }

  function clearReviewKnowledge() {
    setReviews([]);
    setKnowledgeCandidates([]);
    setKnowledgePacks([]);
    setKnowledgeMetrics(null);
  }

  async function refreshAuditLogs(id = taskId) {
    if (!id) {
      setAuditLogs([]);
      return;
    }
    const logs = await api.listAuditLogs(id);
    setAuditLogs(logs.items);
  }

  async function approveReview(reviewId: string) {
    await runKnowledgeAction(async () => {
      await api.approveReview(reviewId, true);
    });
  }

  async function rejectReview(reviewId: string) {
    await runKnowledgeAction(async () => {
      await api.rejectReview(reviewId);
    });
  }

  async function acceptCandidate(candidateId: string) {
    await runKnowledgeAction(async () => {
      await api.acceptKnowledgeCandidate(candidateId);
    });
  }

  async function createKnowledgePack() {
    if (!selectedSchema || !selectedTemplate) {
      setError("请先选择 Schema 和 Template。");
      return;
    }
    await runKnowledgeAction(async () => {
      await api.createKnowledgePack(selectedSchema, selectedTemplate);
    });
  }

  async function activateKnowledgePack(packId: string) {
    await runKnowledgeAction(async () => {
      await api.activateKnowledgePack(packId);
    });
  }

  async function runKnowledgeAction(action: () => Promise<void>) {
    setRunState("working");
    setError("");
    try {
      await action();
      await refreshReviewKnowledge();
      setRunState("ready");
    } catch (caught) {
      setRunState("error");
      setError(errorMessage(caught));
    }
  }

  function onSchemaChange(schemaId: string) {
    setSelectedSchema(schemaId);
    const firstTemplate = templates.find((template) => template.schema_id === schemaId);
    setSelectedTemplate(firstTemplate?.template_id ?? "");
  }

  function updateContentOption<K extends keyof ContentOrganizationOptions>(
    key: K,
    value: ContentOrganizationOptions[K]
  ) {
    setContentOptions((current) => ({ ...current, [key]: value }));
  }

  const working = runState === "loading" || runState === "working";
  const completedMappings = mapping?.mappings.length ?? 0;
  const reviewItems = mapping?.review_required_items.length ?? 0;
  const validationErrors =
    validation?.issues.filter((issue) => issue.level === "error").length ?? 0;

  return (
    <main className="app-shell">
      <section className="sidebar">
        <div className="brand-row">
          <div className="brand-mark">
            <FileJson size={22} />
          </div>
          <div>
            <h1>SchemaPack Agent</h1>
            <p>转换工作台</p>
          </div>
        </div>

        <div className="control-group">
          <label htmlFor="schema">Schema</label>
          <select
            id="schema"
            value={selectedSchema}
            onChange={(event) => onSchemaChange(event.target.value)}
          >
            {schemas.map((schema) => (
              <option key={schema.schema_id} value={schema.schema_id}>
                {schema.name} · {schema.version} · {displayStatus(schema.status ?? "active")}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="template">Template</label>
          <select
            id="template"
            value={selectedTemplate}
            onChange={(event) => setSelectedTemplate(event.target.value)}
          >
            {templateOptions.map((template) => (
              <option key={template.template_id} value={template.template_id}>
                {template.name} · {template.version} · {displayStatus(template.status ?? "active")}
              </option>
            ))}
          </select>
        </div>

        <div className="schema-strip">
          <span>{selectedSchemaModel?.fields?.length ?? 0}</span>
          <small>字段</small>
          <span>
            {selectedSchemaModel?.fields?.filter((field) => field.required).length ?? 0}
          </span>
          <small>必填</small>
        </div>

        <div className="content-options">
          <div className="control-group">
            <label htmlFor="chunk-strategy">Chunk 策略</label>
            <select
              id="chunk-strategy"
              value={contentOptions.chunk_strategy}
              onChange={(event) =>
                updateContentOption(
                  "chunk_strategy",
                  event.target.value as ContentOrganizationOptions["chunk_strategy"]
                )
              }
            >
              <option value="fixed_window">固定窗口</option>
              <option value="heading_aware">标题感知</option>
              <option value="source_block_aware">源块感知</option>
              <option value="table_protect">表格保护</option>
              <option value="parent_child">父子 Chunk</option>
            </select>
          </div>
          <div className="option-grid">
            <NumberField
              id="target-tokens"
              label="目标"
              value={contentOptions.target_tokens}
              min={1}
              onChange={(value) => updateContentOption("target_tokens", value)}
            />
            <NumberField
              id="min-tokens"
              label="最小"
              value={contentOptions.min_tokens}
              min={1}
              onChange={(value) => updateContentOption("min_tokens", value)}
            />
            <NumberField
              id="max-tokens"
              label="最大"
              value={contentOptions.max_tokens}
              min={1}
              onChange={(value) => updateContentOption("max_tokens", value)}
            />
            <NumberField
              id="overlap-tokens"
              label="重叠"
              value={contentOptions.overlap_tokens}
              min={0}
              onChange={(value) => updateContentOption("overlap_tokens", value)}
            />
          </div>
          <div className="check-grid">
            <CheckboxField
              label="表格"
              checked={contentOptions.protect_tables}
              onChange={(checked) => updateContentOption("protect_tables", checked)}
            />
            <CheckboxField
              label="列表"
              checked={contentOptions.protect_lists}
              onChange={(checked) => updateContentOption("protect_lists", checked)}
            />
            <CheckboxField
              label="代码"
              checked={contentOptions.protect_code_blocks}
              onChange={(checked) => updateContentOption("protect_code_blocks", checked)}
            />
            <CheckboxField
              label="父子"
              checked={
                contentOptions.enable_parent_child ||
                contentOptions.chunk_strategy === "parent_child"
              }
              onChange={(checked) => updateContentOption("enable_parent_child", checked)}
            />
          </div>
        </div>

        <div className="button-grid">
          <button type="button" onClick={() => setUirText(sampleUirText)}>
            <ClipboardList size={17} />
            示例
          </button>
          <button type="button" onClick={() => void loadCatalog()} disabled={working}>
            <RefreshCw size={17} />
            刷新
          </button>
        </div>

        <ExternalUirPanel
          currentDocId={docId}
          working={working}
          onStandardUirPreview={setUirText}
          onImported={handleExternalImport}
          onRecommendedRoute={applyRecommendedRoute}
          onTaskCreated={(response) => void handleExternalTaskCreated(response)}
        />

        <SchemaDraftLabPanel />

        <label className="uir-editor-label" htmlFor="uir">
          UIR JSON
        </label>
        <textarea
          id="uir"
          value={uirText}
          onChange={(event) => setUirText(event.target.value)}
          spellCheck={false}
        />

        <div className="action-stack">
          <button type="button" className="primary" onClick={() => void importDocument()} disabled={working}>
            <UploadCloud size={18} />
            导入
          </button>
          <button type="button" onClick={() => void createTask()} disabled={working || !docId}>
            <FileJson size={18} />
            创建 Task
          </button>
          <button type="button" className="accent" onClick={() => void executeTask()} disabled={working || !taskId}>
            <Play size={18} />
            执行
          </button>
        </div>
      </section>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Task</p>
            <h2>{task?.task_id ?? (taskId || "暂无 Task")}</h2>
          </div>
          <StatusBadge status={task?.status ?? runState} />
        </header>

        {error ? (
          <div className="error-banner">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        ) : null}

        <section className="metrics-row">
          <Metric label="文档" value={docId || "-"} />
          <Metric label="已映射" value={String(completedMappings)} />
          <Metric label="待 Review" value={String(reviewItems)} tone={reviewItems ? "amber" : "green"} />
          <Metric label="错误" value={String(validationErrors)} tone={validationErrors ? "red" : "green"} />
        </section>

        <section className="report-grid">
          <ReportPanel title="Mapping 证据" icon={<ClipboardList size={18} />}>
            <MappingEvidencePanel report={mapping} />
          </ReportPanel>

          <ReportPanel title="Validation 问题" icon={<CheckCircle2 size={18} />}>
            <ValidationIssuePanel report={validation} />
          </ReportPanel>

          <ReportPanel title="Chunk 证据" icon={<FileJson size={18} />}>
            <ChunkEvidencePanel report={chunks} />
          </ReportPanel>

          <ReportPanel title="Package Manifest" icon={<Package size={18} />}>
            <PackageManifestPanel manifest={manifest} verifier={verifier} />
          </ReportPanel>

          <ReportPanel title="可信链路" icon={<GitBranch size={18} />}>
            <LineagePanel
              taskId={taskId}
              available={Boolean(task?.report_paths?.lineage_graph)}
            />
          </ReportPanel>

          <ReportPanel title="下游就绪度" icon={<Package size={18} />}>
            <DownstreamReadinessPanel
              manifest={manifest}
              chunks={chunks}
              verifier={verifier}
            />
          </ReportPanel>

          <ReportPanel title="Knowledge 对比" icon={<Tags size={18} />}>
            <KnowledgeComparisonPanel result={knowledgeLoop} />
          </ReportPanel>

          <ReportPanel title="Mapping" icon={<ClipboardList size={18} />}>
            {mapping ? (
              <div className="mapping-list">
                {mapping.mappings.slice(0, 8).map((item) => (
                  <div className="mapping-row" key={String(item.mapping_id)}>
                    <span>{sourceName(item)}</span>
                    <strong>{String(item.target_field_id)}</strong>
                    <em>{displayConfidence(String(item.confidence_tier ?? item.method))}</em>
                    <small>{displayStatus(String(item.status ?? "accepted"))}</small>
                    <TagList label="风险" values={asStringList(item.risk_flags)} />
                    <details className="mapping-evidence">
                      <summary>{String(item.method)}</summary>
                      <EvidenceList item={item} />
                    </details>
                  </div>
                ))}
                {mapping.review_required_items.length ? (
                  <div className="review-box">
                    {mapping.review_required_items.slice(0, 6).map((item) => (
                      <div className="review-candidate" key={String(item.mapping_id)}>
                        <strong>
                          {sourceName(item)} → {String(item.target_field_id)}
                        </strong>
                        <span>
                          {displayConfidence(String(item.confidence_tier ?? "low"))} /{" "}
                          {String(item.review_required_reason ?? "需要 Review")}
                        </span>
                        <TagList label="风险" values={asStringList(item.risk_flags)} />
                        <EvidenceList item={item} />
                      </div>
                    ))}
                  </div>
                ) : null}
                <JsonDetails title="原始 Mapping JSON" data={mapping} />
              </div>
            ) : (
              <EmptyState text="暂无 Mapping 报告" />
            )}
          </ReportPanel>

          <ReportPanel title="Validation" icon={<CheckCircle2 size={18} />}>
            {validation ? (
              <div className="validation-block">
                <div className={validation.passed ? "pass-line" : "fail-line"}>
                  {validation.passed ? "已通过" : "需要处理"}
                </div>
                {validation.issues.length ? (
                  validation.issues.slice(0, 8).map((issue, index) => (
                    <div className="issue-row" key={`${String(issue.code)}-${index}`}>
                      <span>{displayIssueLevel(String(issue.level))}</span>
                      <p>{String(issue.message)}</p>
                    </div>
                  ))
                ) : (
                  <p className="quiet">暂无 Validation 问题。</p>
                )}
                <JsonDetails title="原始 Validation JSON" data={validation} />
              </div>
            ) : (
              <EmptyState text="暂无 Validation 报告" />
            )}
          </ReportPanel>

          <ReportPanel title="内容组织" icon={<Tags size={18} />}>
            {contentOrg ? (
              <div className="content-org-block">
                <div className="content-org-summary">
                  <Metric label="Chunks" value={String(contentOrg.chunk_count)} />
                  <Metric
                    label="摘要"
                    value={coverageText(contentOrg.chunks_with_summary, contentOrg.chunk_count)}
                    tone={contentOrg.chunks_with_summary ? "green" : "amber"}
                  />
                  <Metric
                    label="关键词"
                    value={coverageText(contentOrg.chunks_with_keywords, contentOrg.chunk_count)}
                    tone={contentOrg.chunks_with_keywords ? "green" : "amber"}
                  />
                  <Metric
                    label="链接"
                    value={coverageText(contentOrg.chunks_with_source_links, contentOrg.chunk_count)}
                    tone={contentOrg.chunks_with_source_links ? "green" : "amber"}
                  />
                </div>
                <TagList
                  label="内容标签"
                  values={Object.keys(contentOrg.summary.content_tag_counts ?? {})}
                />
                <TagList
                  label="质量标签"
                  values={Object.keys(contentOrg.summary.quality_tag_counts ?? {})}
                />
                {contentOrg.warnings.length ? (
                  <p className="quiet">{contentOrg.warnings.join(", ")}</p>
                ) : null}
                <JsonDetails title="原始内容组织 JSON" data={contentOrg} />
              </div>
            ) : (
              <EmptyState text="暂无内容组织报告" />
            )}
          </ReportPanel>

          <ReportPanel title="Chunk 预览" icon={<FileJson size={18} />}>
            {chunks ? (
              <div className="chunk-preview-block">
                <p className="quiet">
                  显示前 {Math.min(chunks.items.length, 4)} 个，共 {chunks.total} 个 Chunk。
                </p>
                {chunks.items.slice(0, 4).map((chunk) => (
                  <div className="chunk-card" key={chunk.chunk_id}>
                    <div className="chunk-card-head">
                      <strong>{chunk.chunk_id}</strong>
                      <span>{displayChunkStrategy(chunk.strategy)}</span>
                    </div>
                    <div className="chunk-meta">
                      <span>{displayChunkGranularity(chunk.granularity)}</span>
                      <span>{chunk.token_estimate ?? 0} token</span>
                      <span>{chunk.char_count ?? chunk.text.length} 字符</span>
                    </div>
                    {chunk.parent_chunk_id ? (
                       <small>父 Chunk: {chunk.parent_chunk_id}</small>
                    ) : null}
                    {chunk.title_path?.length ? (
                       <small>标题路径: {chunk.title_path.join(" / ")}</small>
                    ) : null}
                    <p>{chunk.summary || chunk.text.slice(0, 180)}</p>
                    <TagList label="关键词" values={chunk.keywords ?? []} />
                    <TagList
                      label="内容"
                      values={chunk.content_tags ?? chunk.tags?.content ?? []}
                    />
                    <TagList
                      label="质量"
                      values={chunk.quality_flags?.length ? chunk.quality_flags : chunk.quality_tags ?? chunk.tags?.quality ?? []}
                    />
                    <small>
                      来源:{" "}
                      {(chunk.source_block_ids ?? []).join(", ") ||
                        `${chunk.source_links?.length ?? 0} 个链接`}
                    </small>
                  </div>
                ))}
                <JsonDetails title="原始 Chunk JSON" data={chunks} />
              </div>
            ) : (
              <EmptyState text="暂无 Chunk 预览" />
            )}
          </ReportPanel>

          <ReportPanel title="Package" icon={<Package size={18} />}>
            {pkg ? (
              <div className="package-block">
                <div className="package-id">{pkg.package_id}</div>
                <dl>
                  <div>
                    <dt>状态</dt>
                    <dd>{displayStatus(pkg.status)}</dd>
                  </div>
                  <div>
                    <dt>SHA-256</dt>
                    <dd>{pkg.sha256 ?? "-"}</dd>
                  </div>
                </dl>
                {taskId ? (
                  <a className="download-link" href={api.packageDownloadUrl(taskId)}>
                    <Package size={17} />
                    下载 ZIP
                  </a>
                ) : null}
              </div>
            ) : (
              <EmptyState text="暂无 Package" />
            )}
          </ReportPanel>

          <ReportPanel title="Audit 日志" icon={<ClipboardList size={18} />}>
            {auditLogs.length ? (
              <div className="audit-list">
                {auditLogs.slice(0, 6).map((log) => (
                  <div className="audit-row" key={log.audit_id}>
                    <strong>{log.action}</strong>
                    <span>{log.success ? "成功" : "失败"}</span>
                    <small>{log.path ?? "-"}</small>
                    <JsonDetails title="元数据" data={log.metadata} />
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState text="暂无 Audit 日志" />
            )}
          </ReportPanel>

          <ReportPanel title="Review 队列" icon={<ClipboardList size={18} />}>
            {reviews.length ? (
              <div className="review-list">
                {reviews.slice(0, 6).map((review) => (
                  <div className="review-item" key={review.review_id}>
                    <div>
                      <strong>{review.source_field_name ?? "-"}</strong>
                      <span>{review.target_field_id ?? "-"}</span>
                      <em>{review.confidence === null ? "-" : review.confidence.toFixed(2)}</em>
                    </div>
                    {review.reason ? <p className="quiet">{review.reason}</p> : null}
                    <div className="inline-actions">
                      <button
                        type="button"
                        onClick={() => void approveReview(review.review_id)}
                        disabled={working}
                      >
                        通过
                      </button>
                      <button
                        type="button"
                        onClick={() => void rejectReview(review.review_id)}
                        disabled={working}
                      >
                        拒绝
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState text="暂无待处理 Review" />
            )}
          </ReportPanel>

          <ReportPanel title="Knowledge Packs" icon={<Tags size={18} />}>
            <div className="knowledge-block">
              <div className="content-org-summary">
                <Metric
                  label="候选"
                  value={String(knowledgeMetrics?.pending_candidates ?? 0)}
                  tone={(knowledgeMetrics?.pending_candidates ?? 0) ? "amber" : "neutral"}
                />
                <Metric
                  label="已接受"
                  value={String(knowledgeMetrics?.accepted_candidates ?? 0)}
                  tone={(knowledgeMetrics?.accepted_candidates ?? 0) ? "green" : "neutral"}
                />
                <Metric
                  label="草稿"
                  value={String(knowledgeMetrics?.draft_packs ?? 0)}
                  tone={(knowledgeMetrics?.draft_packs ?? 0) ? "amber" : "neutral"}
                />
                <Metric
                  label="已激活"
                  value={String(knowledgeMetrics?.active_packs ?? 0)}
                  tone={(knowledgeMetrics?.active_packs ?? 0) ? "green" : "neutral"}
                />
              </div>
              {knowledgeCandidates.filter((candidate) => candidate.status === "pending").length ? (
                <div className="knowledge-list">
                  {knowledgeCandidates
                    .filter((candidate) => candidate.status === "pending")
                    .slice(0, 5)
                    .map((candidate) => (
                      <div className="knowledge-row" key={candidate.candidate_id}>
                        <span>{candidate.alias}</span>
                        <strong>{candidate.target_field_id}</strong>
                        <button
                          type="button"
                          onClick={() => void acceptCandidate(candidate.candidate_id)}
                          disabled={working}
                        >
                          接受
                        </button>
                      </div>
                    ))}
                </div>
              ) : null}
              <button
                type="button"
                onClick={() => void createKnowledgePack()}
                disabled={working || !knowledgeCandidates.some((candidate) => candidate.status === "accepted")}
              >
                创建 Pack
              </button>
              {knowledgePacks.length ? (
                <div className="knowledge-list">
                  {knowledgePacks.slice(0, 5).map((pack) => (
                    <div className="knowledge-row" key={pack.pack_id}>
                      <span>{pack.name}</span>
                      <strong>{displayStatus(pack.status)}</strong>
                      {pack.status === "draft" ? (
                        <button
                          type="button"
                          onClick={() => void activateKnowledgePack(pack.pack_id)}
                          disabled={working}
                        >
                          激活
                        </button>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </ReportPanel>

          <ReportPanel title="Review Workbench" icon={<Users size={18} />}>
            <ReviewWorkbenchPanel />
          </ReportPanel>

          <ReportPanel title="Evaluation Center" icon={<BarChart3 size={18} />}>
            <EvaluationCenterPanel />
          </ReportPanel>
        </section>
      </section>
    </main>
  );
}

function Metric({
  label,
  value,
  tone = "neutral"
}: {
  label: string;
  value: string;
  tone?: "neutral" | "green" | "amber" | "red";
}) {
  return (
    <div className={`metric metric-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ReportPanel({
  title,
  icon,
  children
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <article className="report-panel">
      <header>
        {icon}
        <h3>{title}</h3>
      </header>
      {children}
    </article>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}

function NumberField({
  id,
  label,
  value,
  min,
  onChange
}: {
  id: string;
  label: string;
  value: number;
  min: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="control-group">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="number"
        min={min}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </div>
  );
}

function CheckboxField({
  label,
  checked,
  onChange
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="checkbox-field">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span>{label}</span>
    </label>
  );
}

function EvidenceList({ item }: { item: Record<string, any> }) {
  const evidence = Array.isArray(item.evidence) ? item.evidence : [];
  const evidenceText = asStringList(item.evidence_text);
  const messages = evidence.length
    ? evidence
        .map((entry) =>
          entry && typeof entry === "object"
            ? String(entry.message ?? entry.type ?? "")
            : String(entry)
        )
        .filter(Boolean)
    : evidenceText;
  if (!messages.length) {
    return null;
  }
  return (
    <ul className="evidence-list">
      {messages.slice(0, 4).map((message, index) => (
        <li key={`${message}-${index}`}>{message}</li>
      ))}
    </ul>
  );
}

function TagList({ label, values }: { label: string; values: string[] }) {
  return (
    <div className="tag-list">
      <span>{label}</span>
      <div>
        {values.length ? values.slice(0, 10).map((value) => <em key={value}>{value}</em>) : "-"}
      </div>
    </div>
  );
}

function asStringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.length > 0)
    : [];
}

function JsonDetails({ title, data }: { title: string; data: unknown }) {
  return (
    <details className="json-details">
      <summary>{title}</summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}

function StatusBadge({ status }: { status: string }) {
  return <div className={`status-badge status-${status}`}>{displayStatus(status)}</div>;
}

function displayStatus(status: string) {
  const labels: Record<string, string> = {
    idle: "空闲",
    loading: "加载中",
    ready: "就绪",
    working: "处理中",
    error: "错误",
    pending: "待处理",
    accepted: "已接受",
    rejected: "已拒绝",
    draft: "草稿",
    active: "已激活",
    archived: "已归档",
    completed: "已完成",
    failed: "失败",
    success: "成功"
  };
  return labels[status] ?? status;
}

function displayIssueLevel(level: string) {
  const labels: Record<string, string> = {
    error: "错误",
    warning: "警告",
    warn: "警告",
    info: "提示",
    issue: "问题"
  };
  return labels[level.toLowerCase()] ?? level;
}

function displayConfidence(value: string) {
  const labels: Record<string, string> = {
    high: "高",
    medium: "中",
    low: "低",
    accepted: "已接受",
    review: "待 Review"
  };
  return labels[value.toLowerCase()] ?? value;
}

function displayChunkStrategy(strategy: string | null | undefined) {
  const labels: Record<string, string> = {
    fixed_window: "固定窗口",
    heading_aware: "标题感知",
    source_block_aware: "源块感知",
    table_protect: "表格保护",
    parent_child: "父子 Chunk",
    legacy: "旧策略"
  };
  return strategy ? labels[strategy] ?? strategy : "旧策略";
}

function displayChunkGranularity(granularity: string | null | undefined) {
  const labels: Record<string, string> = {
    chunk: "Chunk",
    paragraph: "段落",
    section: "章节",
    table: "表格"
  };
  return granularity ? labels[granularity] ?? granularity : "Chunk";
}

function sourceName(item: Record<string, any>) {
  const source = item.source_field;
  if (source && typeof source === "object" && "source_name" in source) {
    return String(source.source_name);
  }
  return "-";
}

function coverageText(count: number, total: number) {
  return total ? `${count}/${total}` : "0/0";
}

function errorMessage(caught: unknown) {
  return caught instanceof Error ? caught.message : "发生未知错误";
}

export default App;
