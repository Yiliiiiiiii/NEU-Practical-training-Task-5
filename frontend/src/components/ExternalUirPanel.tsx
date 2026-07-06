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
  currentDocId: string;
  working: boolean;
  onStandardUirPreview: (uirText: string) => void;
  onImported: (response: ExternalUirImportResponse) => void;
  onRecommendedRoute: (route: ExternalUirRouteReport) => void;
  onTaskCreated: (response: TaskCreateResponse) => void;
};

export function ExternalUirPanel({
  currentDocId,
  working,
  onStandardUirPreview,
  onImported,
  onRecommendedRoute,
  onTaskCreated
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
    currentDocId && routeSelection?.canCreate
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
      llmUsed: report.llm_used ? "true" : "false",
      autoAccepted: report.llm_auto_accepted_count
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
          ? `Detected ${detected.selected_adapter.adapter_id}.`
          : "Unsupported dialect. Manual review is required."
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
      setRouteOverride("");
      setRouteConfirmed(false);
      onStandardUirPreview(JSON.stringify(converted.standard_uir, null, 2));
      if (converted.route_report) {
        onRecommendedRoute(converted.route_report);
      }
      setMessage("External UIR converted. Review the preview before importing.");
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
      setRouteOverride("");
      setRouteConfirmed(false);
      onImported(imported);
      if (imported.route_report) {
        onRecommendedRoute(imported.route_report);
      }
      setMessage(`Imported ${imported.doc_id}. Create a task only after confirming the route.`);
    });
  }

  async function createTaskFromRoute() {
    if (!recommendedRoute || !routeSelection?.schemaId || !routeSelection.templateId) {
      setStatus("error");
      setMessage("Select and confirm a schema/template before creating the task.");
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
      setMessage(
        created.review_required
          ? "Task created. Route review is still required."
          : "Task created from the recommended route."
      );
    });
  }

  function parsePayload(): Record<string, unknown> {
    const parsed = JSON.parse(jsonText);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("External UIR JSON must be an object.");
    }
    return parsed as Record<string, unknown>;
  }

  async function runPanelAction(action: () => Promise<void>) {
    setStatus("working");
    setMessage("");
    try {
      await action();
      setStatus("ready");
    } catch (caught) {
      setStatus("error");
      setMessage(caught instanceof Error ? caught.message : "External UIR operation failed.");
    }
  }

  async function onFileSelected(file: File | null) {
    if (!file) {
      return;
    }
    setJsonText(await file.text());
  }

  return (
    <section className="external-uir-panel" aria-label="External UIR Adapter">
      <div className="external-uir-head">
        <div>
          <h3>External UIR Adapter</h3>
          <p>Convert upstream External UIR JSON into a standard UIRDocument.</p>
        </div>
        <GitBranch size={18} />
      </div>

      <div className="external-uir-grid">
        <div className="control-group">
          <label htmlFor="external-source">Source System</label>
          <input
            id="external-source"
            value={sourceSystem}
            onChange={(event) => setSourceSystem(event.target.value)}
          />
        </div>
        <div className="control-group">
          <label htmlFor="external-dialect">Dialect Hint</label>
          <select
            id="external-dialect"
            value={dialectHint}
            onChange={(event) => setDialectHint(event.target.value)}
          >
            <option value="auto">auto</option>
            {adapters.map((adapter) => (
              <option key={adapter.adapter_id} value={adapter.adapter_id}>
                {adapter.adapter_id}
              </option>
            ))}
          </select>
        </div>
      </div>

      <label className="file-button" htmlFor="external-json-file">
        <FileInput size={16} />
        Upload JSON
      </label>
      <input
        id="external-json-file"
        className="visually-hidden-input"
        type="file"
        accept="application/json,.json"
        onChange={(event) => void onFileSelected(event.currentTarget.files?.[0] ?? null)}
      />

      <div className="external-toggles">
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={routeSchema}
            onChange={(event) => setRouteSchema(event.target.checked)}
          />
          <span>Route Schema</span>
        </label>
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={allowLlm}
            onChange={(event) => setAllowLlm(event.target.checked)}
          />
          <span>DeepSeek</span>
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
          <SearchCheck size={16} />
          Detect
        </button>
        <button type="button" onClick={() => void convert()} disabled={working || status === "working"}>
          <Wand2 size={16} />
          Convert & Preview
        </button>
        <button
          type="button"
          className="primary"
          onClick={() => void importStandardUir()}
          disabled={working || status === "working" || !result}
        >
          <UploadCloud size={16} />
          Import Standard UIR
        </button>
        <button
          type="button"
          className="accent"
          onClick={() => void createTaskFromRoute()}
          disabled={working || status === "working" || !canCreateTask}
        >
          <CheckCircle2 size={16} />
          Create Task
        </button>
      </div>

      {message ? <p className={`external-message external-${status}`}>{message}</p> : null}

      {adapterSummary ? (
        <div className="external-summary">
          <span>adapter</span>
          <strong>{adapterSummary.adapter}</strong>
          <span>dialect</span>
          <strong>{adapterSummary.dialect}</strong>
          <span>blocks</span>
          <strong>{adapterSummary.blocks}</strong>
          <span>trace</span>
          <strong>{adapterSummary.traces}</strong>
          <span>coverage</span>
          <strong>{adapterSummary.traceCoverage}</strong>
          <span>LLM</span>
          <strong>{adapterSummary.llmUsed}</strong>
          <span>auto accepted</span>
          <strong>{adapterSummary.autoAccepted}</strong>
        </div>
      ) : null}

      {detection ? (
        <div className="external-detection">
          <div>
            <span>Detected Adapter</span>
            <strong>{detection.selected_adapter?.adapter_id ?? "unsupported"}</strong>
            {detection.selected_adapter ? (
              <em>{Math.round(detection.selected_adapter.confidence * 100)}%</em>
            ) : null}
          </div>
          {detection.review_required ? <small>review required</small> : null}
          {detection.alternatives.length ? (
            <p>
              {detection.alternatives
                .map((item) => `${item.adapter_id} ${Math.round(item.confidence * 100)}%`)
                .join(" / ")}
            </p>
          ) : null}
        </div>
      ) : null}

      {result?.warnings.length ? (
        <div className="external-warning-list">
          {result.warnings.map((warning) => (
            <span key={warning}>{warning}</span>
          ))}
        </div>
      ) : null}

      {recommendedRoute ? (
        <div className="external-route">
          <div className="external-route-head">
            <span>Recommended</span>
            <em>{Math.round(recommendedRoute.confidence * 100)}%</em>
          </div>
          <div className="external-confidence" aria-label="Route confidence">
            <span style={{ width: `${Math.round(recommendedRoute.confidence * 100)}%` }} />
          </div>
          <strong>
            {recommendedRoute.selected_schema_id ?? "No automatic selection"} /{" "}
            {recommendedRoute.selected_template_id ?? "-"}
          </strong>
          <label className="control-group" htmlFor="external-route-override">
            <span>Schema / Template</span>
            <select
              id="external-route-override"
              value={routeOverride}
              onChange={(event) => {
                setRouteOverride(event.target.value);
                setRouteConfirmed(false);
              }}
            >
              <option value="">Use recommended route</option>
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
                {candidate.risk_flags.length ? (
                  <small>{candidate.risk_flags.join(", ")}</small>
                ) : null}
              </div>
            ))}
          </div>
          <details className="external-route-evidence">
            <summary>Route evidence</summary>
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
                onChange={(event) => setRouteConfirmed(event.target.checked)}
              />
              <span>Confirm reviewed schema/template selection</span>
            </label>
          ) : null}
          <small className="external-task-notice">
            Creates the task only. Execution remains a separate action.
          </small>
        </div>
      ) : null}

      {result ? (
        <details className="json-details external-details">
          <summary>Adapter report JSON</summary>
          <pre>{JSON.stringify(result.adapter_report, null, 2)}</pre>
        </details>
      ) : null}
    </section>
  );
}
