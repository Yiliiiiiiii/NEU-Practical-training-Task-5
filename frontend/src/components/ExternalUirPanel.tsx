import { CheckCircle2, FileInput, GitBranch, SearchCheck, UploadCloud, Wand2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api";
import { resolveRouteSelection } from "../routeSelection";
import type {
  ExternalUirAdapterCapability,
  ExternalUirAdapterDetectResponse,
  ExternalUirConvertResponse,
  ExternalUirImportResponse,
  ExternalUirRouteReport,
  TaskCreateResponse
} from "../types";

type ExternalUirPanelProps = {
  currentDocId?: string;
  working: boolean;
  onStandardUirPreview: (uirText: string) => void;
  onImported: (response: ExternalUirImportResponse) => void;
  onRecommendedRoute: (route: ExternalUirRouteReport) => void;
  onTaskCreated?: (response: TaskCreateResponse) => void;
  onRouteConfirmationChange?: (confirmed: boolean) => void;
  enableTaskCreation?: boolean;
};

export function ExternalUirPanel({
  currentDocId = "",
  working,
  onStandardUirPreview,
  onImported,
  onRecommendedRoute,
  onTaskCreated,
  onRouteConfirmationChange,
  enableTaskCreation = false
}: ExternalUirPanelProps) {
  const [sourceSystem, setSourceSystem] = useState("topic11");
  const [dialectHint, setDialectHint] = useState("auto");
  const [routeSchema, setRouteSchema] = useState(true);
  const [allowLlm, setAllowLlm] = useState(false);
  const [jsonText, setJsonText] = useState("");
  const [adapters, setAdapters] = useState<ExternalUirAdapterCapability[]>([]);
  const [detection, setDetection] = useState<ExternalUirAdapterDetectResponse | null>(null);
  const [result, setResult] = useState<ExternalUirConvertResponse | null>(null);
  const [routeOverride, setRouteOverride] = useState("");
  const [routeConfirmed, setRouteConfirmed] = useState(false);
  const [status, setStatus] = useState<"idle" | "working" | "ready" | "error">("idle");
  const [message, setMessage] = useState("");

  const recommendedRoute = result?.route_report ?? null;
  const routeSelection = recommendedRoute
    ? resolveRouteSelection(recommendedRoute, routeOverride, routeConfirmed)
    : null;
  const canCreateTask = Boolean(
    enableTaskCreation && currentDocId && routeSelection?.canCreate && onTaskCreated
  );

  const adapterSummary = useMemo(() => {
    if (!result) {
      return null;
    }
    const report = result.adapter_report;
    return {
      adapter: report.adapter_id ?? "legacy",
      dialect:
        report.detected_dialect ??
        result.standard_uir?.metadata?.external_uir_adapter_version ??
        report.adapter_version,
      blocks: Array.isArray(result.standard_uir?.blocks) ? result.standard_uir.blocks.length : 0,
      traces: report.trace_items.length,
      traceCoverage: `${Math.round((report.trace_coverage ?? 0) * 100)}%`,
      llmUsed: report.llm_used
    };
  }, [result]);

  useEffect(() => {
    let cancelled = false;
    void api
      .listExternalUirAdapters()
      .then((response) => {
        if (!cancelled) {
          setAdapters(response.items);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAdapters([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function detectAdapter() {
    await runPanelAction(async () => {
      const payload = parsePayload();
      const detected = await api.detectExternalUirAdapter({
        payload,
        source_system: sourceSystem,
        dialect_hint: dialectHint
      });
      setDetection(detected);
      setMessage(
        detected.selected_adapter
          ? `已检测到 ${detected.selected_adapter.adapter_id}。`
          : "未找到可用方言，需要人工复核。"
      );
    });
  }

  async function convert() {
    await runPanelAction(async () => {
      const payload = parsePayload();
      const converted = await api.convertExternalUir({
        payload,
        source_system: sourceSystem,
        dialect_hint: dialectHint === "auto" ? "auto" : dialectHint,
        route_schema: routeSchema,
        allow_llm: allowLlm,
        llm_mode: allowLlm ? "deepseek" : null
      });
      setResult(converted);
      resetRouteConfirmation();
      onStandardUirPreview(JSON.stringify(converted.standard_uir, null, 2));
      if (converted.route_report) {
        onRecommendedRoute(converted.route_report);
      }
      setMessage("External UIR 已转换，请检查预览后再导入。"
      );
    });
  }

  async function importStandardUir() {
    await runPanelAction(async () => {
      const payload = parsePayload();
      const imported = await api.importExternalUir({
        payload,
        source_system: sourceSystem,
        dialect_hint: dialectHint === "auto" ? "auto" : dialectHint,
        route_schema: routeSchema,
        allow_llm: allowLlm,
        llm_mode: allowLlm ? "deepseek" : null
      });
      setResult({
        standard_uir: result?.standard_uir ?? {},
        adapter_report: imported.adapter_report,
        route_report: imported.route_report,
        warnings: imported.warnings,
        errors: []
      });
      resetRouteConfirmation();
      onImported(imported);
      if (imported.route_report) {
        onRecommendedRoute(imported.route_report);
      }
      setMessage(`已导入 ${imported.doc_id}。请继续选择 SchemaPack。`);
    });
  }

  async function createTaskFromRoute() {
    if (!recommendedRoute || !routeSelection?.schemaId || !routeSelection.templateId || !onTaskCreated) {
      setStatus("error");
      setMessage("请先选择并确认 Schema / 模板。"
      );
      return;
    }
    await runPanelAction(async () => {
      const created = await api.createExternalUirTask({
        doc_id: currentDocId,
        schema_id: routeSelection.schemaId,
        template_id: routeSelection.templateId,
        route_report: recommendedRoute,
        adapter_report: result?.adapter_report ?? null
      });
      onTaskCreated(created);
      setMessage(created.review_required ? "已创建任务，路由仍需复核。" : "已按所选路由创建任务。"
      );
    });
  }

  function parsePayload(): Record<string, unknown> {
    const parsed = JSON.parse(jsonText);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("External UIR JSON 必须是对象。"
      );
    }
    return parsed as Record<string, unknown>;
  }

  function resetRouteConfirmation() {
    setRouteOverride("");
    setRouteConfirmed(false);
    onRouteConfirmationChange?.(false);
  }

  async function runPanelAction(action: () => Promise<void>) {
    setStatus("working");
    setMessage("");
    try {
      await action();
      setStatus("ready");
    } catch (caught) {
      setStatus("error");
      setMessage(caught instanceof Error ? caught.message : "External UIR 操作失败。"
      );
    }
  }

  async function onFileSelected(file: File | null) {
    if (file) {
      setJsonText(await file.text());
    }
  }

  return (
    <section className="external-uir-panel" aria-label="External UIR 适配">
      <div className="external-uir-head">
        <div>
          <h3>External UIR 适配</h3>
          <p>将上游 External UIR JSON 转换为标准 UIRDocument。</p>
        </div>
        <GitBranch size={18} aria-hidden="true" />
      </div>

      <div className="external-uir-grid">
        <div className="control-group">
          <label htmlFor="external-source">来源系统</label>
          <input
            id="external-source"
            value={sourceSystem}
            onChange={(event) => setSourceSystem(event.target.value)}
          />
        </div>
        <div className="control-group">
          <label htmlFor="external-dialect">方言提示</label>
          <select
            id="external-dialect"
            value={dialectHint}
            onChange={(event) => setDialectHint(event.target.value)}
          >
            <option value="auto">自动</option>
            {adapters.map((adapter) => (
              <option key={adapter.adapter_id} value={adapter.adapter_id}>
                {adapter.adapter_id}
              </option>
            ))}
          </select>
        </div>
      </div>

      <details>
        <summary>兼容导入</summary>
        <label className="file-button" htmlFor="external-json-file">
          <FileInput size={16} aria-hidden="true" />
          选择 JSON 文件
        </label>
        <input
          id="external-json-file"
          className="visually-hidden-input"
          type="file"
          accept="application/json,.json"
          onChange={(event) => void onFileSelected(event.currentTarget.files?.[0] ?? null)}
        />
      </details>

      <div className="external-toggles">
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={routeSchema}
            onChange={(event) => setRouteSchema(event.target.checked)}
          />
          <span>启用确定性 Schema 路由</span>
        </label>
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={allowLlm}
            onChange={(event) => setAllowLlm(event.target.checked)}
          />
          <span>允许 LLM 辅助</span>
        </label>
      </div>

      <textarea
        className="external-json-editor"
        aria-label="External UIR JSON"
        value={jsonText}
        onChange={(event) => setJsonText(event.target.value)}
        placeholder='{"id":"external_doc_001","chunks":[{"type":"title","text":"..."}]}'
        spellCheck={false}
      />

      <div className="external-actions">
        <button type="button" onClick={() => void detectAdapter()} disabled={working || status === "working"}>
          <SearchCheck size={16} aria-hidden="true" />
          检测适配器
        </button>
        <button type="button" onClick={() => void convert()} disabled={working || status === "working"}>
          <Wand2 size={16} aria-hidden="true" />
          转换并预览
        </button>
        <button
          type="button"
          className="primary"
          onClick={() => void importStandardUir()}
          disabled={working || status === "working" || !result}
        >
          <UploadCloud size={16} aria-hidden="true" />
          导入标准 UIR
        </button>
        {enableTaskCreation ? (
          <button
            type="button"
            className="accent"
            onClick={() => void createTaskFromRoute()}
            disabled={working || status === "working" || !canCreateTask}
          >
            <CheckCircle2 size={16} aria-hidden="true" />
            创建任务
          </button>
        ) : null}
      </div>

      {message ? <p className={`external-message external-${status}`}>{message}</p> : null}

      {adapterSummary ? (
        <div className="external-summary">
          <span>适配器</span>
          <strong>{adapterSummary.adapter}</strong>
          <span>方言</span>
          <strong>{adapterSummary.dialect}</strong>
          <span>区块</span>
          <strong>{adapterSummary.blocks}</strong>
          <span>追溯项</span>
          <strong>{adapterSummary.traces}</strong>
          <span>覆盖率</span>
          <strong>{adapterSummary.traceCoverage}</strong>
          <span>LLM 建议</span>
          <strong>{adapterSummary.llmUsed ? "建议待人工处理（未自动采纳）" : "未使用"}</strong>
        </div>
      ) : null}

      {detection ? (
        <div className="external-detection">
          <div>
            <span>检测到的适配器</span>
            <strong>{detection.selected_adapter?.adapter_id ?? "不支持"}</strong>
            {detection.selected_adapter ? (
              <em>{Math.round(detection.selected_adapter.confidence * 100)}%</em>
            ) : null}
          </div>
          {detection.review_required ? <small>需要人工复核</small> : null}
          {detection.alternatives.length ? (
            <p>{detection.alternatives.map((item) => `${item.adapter_id} ${Math.round(item.confidence * 100)}%`).join(" / ")}</p>
          ) : null}
        </div>
      ) : null}

      {result?.warnings.length ? (
        <div className="external-warning-list" aria-label="转换警告">
          {result.warnings.map((warning) => (
            <span key={warning}>{warning}</span>
          ))}
        </div>
      ) : null}

      {result?.adapter_report.llm_used ? (
        <details className="external-route-evidence">
          <summary>LLM 建议（未自动采纳）</summary>
          {result.adapter_report.assisted_suggestions.length ? (
            result.adapter_report.assisted_suggestions.map((suggestion) => (
              <p key={`${suggestion.external_path}-${suggestion.target_uir_location}`}>
                <strong>{suggestion.external_path}</strong>
                <span>{suggestion.reason}</span>
                <small>{Math.round(suggestion.confidence * 100)}%</small>
              </p>
            ))
          ) : (
            <p>LLM 建议（未自动采纳）</p>
          )}
        </details>
      ) : null}

      {recommendedRoute ? (
        <div className="external-route">
          <div className="external-route-head">
            <span>路由建议</span>
            <em>{Math.round(recommendedRoute.confidence * 100)}%</em>
          </div>
          <div className="external-confidence" aria-label="路由置信度">
            <span style={{ width: `${Math.round(recommendedRoute.confidence * 100)}%` }} />
          </div>
          <strong>
            {recommendedRoute.selected_schema_id ?? "未自动选择"} / {recommendedRoute.selected_template_id ?? "-"}
          </strong>
          <label className="control-group" htmlFor="external-route-override">
            <span>人工选择 Schema / 模板</span>
            <select
              id="external-route-override"
              value={routeOverride}
              onChange={(event) => {
                setRouteOverride(event.target.value);
                setRouteConfirmed(false);
                onRouteConfirmationChange?.(false);
              }}
            >
              <option value="">使用路由建议</option>
              {recommendedRoute.candidates.map((candidate) => (
                <option key={candidate.schema_id} value={candidate.schema_id}>
                  {candidate.schema_id} / {candidate.template_id}
                </option>
              ))}
            </select>
          </label>
          <div className="external-route-candidates">
            {recommendedRoute.candidates.slice(0, 3).map((candidate) => (
              <div key={candidate.schema_id}>
                <strong>{candidate.schema_id}</strong>
                <em>{Math.round(candidate.confidence * 100)}%</em>
                {candidate.risk_flags.length ? <small>{candidate.risk_flags.join(", ")}</small> : null}
              </div>
            ))}
          </div>
          <details className="external-route-evidence">
            <summary>路由证据</summary>
            {recommendedRoute.candidates[0]?.evidence.map((item, index) => (
              <p key={`${item.evidence_type}-${item.value}-${index}`}>
                <strong>{item.evidence_type}</strong>
                <span>{item.value}</span>
                <small>{item.source_path ?? "adapter"}</small>
              </p>
            ))}
          </details>
          {recommendedRoute.review_required ? (
            <label className="checkbox-field external-route-confirm">
              <input
                type="checkbox"
                checked={routeConfirmed}
                onChange={(event) => {
                  setRouteConfirmed(event.target.checked);
                  onRouteConfirmationChange?.(event.target.checked);
                }}
              />
              <span>已人工确认 Schema / 模板选择</span>
            </label>
          ) : null}
          {enableTaskCreation ? <small className="external-task-notice">仅创建任务，执行仍需单独操作。</small> : null}
        </div>
      ) : null}

      {result ? (
        <details className="json-details external-details">
          <summary>适配报告 JSON</summary>
          <pre>{JSON.stringify(result.adapter_report, null, 2)}</pre>
        </details>
      ) : null}
    </section>
  );
}
