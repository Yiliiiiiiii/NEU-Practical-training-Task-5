import { CheckCircle2, Database, Play, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";

import { api } from "../api/client";
import type { JsonObject, MappingTemplate, TargetSchema, TaskCreateResponse } from "../api/types";
import { JsonWorkbench } from "../components/JsonWorkbench";
import generalTemplate from "../demo/mapping_template_general.json";
import policyTemplate from "../demo/mapping_template_policy.json";
import generalSchema from "../demo/target_schema_general.json";
import policySchema from "../demo/target_schema_policy.json";
import generalUir from "../demo/example_uir_general_doc.json";
import policyUir from "../demo/example_uir_policy_doc.json";
import type { ToastInput, WorkbenchSelection } from "../appTypes";

type ResourceKey = "uir" | "schema" | "template";
type DemoKey = "general" | "policy";

interface ImportPageProps {
  onSelectionChange?: (selection: WorkbenchSelection) => void;
  onToast?: (toast: ToastInput) => void;
}

interface ImportResult {
  docId: string;
  schemaId: string;
  templateId: string;
  taskId: string;
  status: string;
}

const DEMOS: Record<
  DemoKey,
  { label: string; uir: JsonObject; schema: TargetSchema; template: MappingTemplate }
> = {
  general: {
    label: "general",
    uir: generalUir as unknown as JsonObject,
    schema: generalSchema as unknown as TargetSchema,
    template: generalTemplate as unknown as MappingTemplate,
  },
  policy: {
    label: "policy",
    uir: policyUir as unknown as JsonObject,
    schema: policySchema as unknown as TargetSchema,
    template: policyTemplate as unknown as MappingTemplate,
  },
};

const PANEL_COPY: Record<ResourceKey, { title: string; description: string }> = {
  uir: {
    title: "UIR Document",
    description: "Normalized document with metadata, blocks, assets, and source anchors.",
  },
  schema: {
    title: "Target Schema",
    description: "Canonical field contract with required fields, types, and constraints.",
  },
  template: {
    title: "Mapping Template",
    description: "Aliases, regex rules, transforms, defaults, and enum maps.",
  },
};

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function parseJsonObject(raw: string): { value: JsonObject | null; error: string | null } {
  try {
    const value = JSON.parse(raw) as unknown;
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return { value: null, error: "JSON must be an object." };
    }
    return { value: value as JsonObject, error: null };
  } catch (error) {
    return {
      value: null,
      error: error instanceof Error ? error.message : "Invalid JSON.",
    };
  }
}

function initialTexts() {
  return {
    uir: formatJson(DEMOS.general.uir),
    schema: formatJson(DEMOS.general.schema),
    template: formatJson(DEMOS.general.template),
  };
}

export function ImportPage({ onSelectionChange, onToast }: ImportPageProps) {
  const [texts, setTexts] = useState<Record<ResourceKey, string>>(() => initialTexts());
  const [activeDemo, setActiveDemo] = useState<DemoKey>("general");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);

  const parsed = useMemo(
    () => ({
      uir: parseJsonObject(texts.uir),
      schema: parseJsonObject(texts.schema),
      template: parseJsonObject(texts.template),
    }),
    [texts],
  );
  const hasErrors = Object.values(parsed).some((entry) => entry.error);

  function loadDemo(key: DemoKey) {
    setActiveDemo(key);
    setTexts({
      uir: formatJson(DEMOS[key].uir),
      schema: formatJson(DEMOS[key].schema),
      template: formatJson(DEMOS[key].template),
    });
    setResult(null);
  }

  async function handleCreateTask() {
    if (!parsed.uir.value || !parsed.schema.value || !parsed.template.value || hasErrors) {
      onToast?.({
        tone: "warning",
        title: "JSON needs attention",
        detail: "Fix the highlighted JSON before creating a task.",
      });
      return;
    }

    setIsSubmitting(true);
    try {
      const documentResponse = await api.importDocument(parsed.uir.value);
      const schemaResponse = await api.createSchema(parsed.schema.value as unknown as TargetSchema);
      const templateResponse = await api.createTemplate(
        parsed.template.value as unknown as MappingTemplate,
      );
      const taskResponse: TaskCreateResponse = await api.createTask({
        doc_id: documentResponse.doc_id,
        schema_id: schemaResponse.schema_id,
        template_id: templateResponse.template_id,
        schema_version:
          typeof parsed.schema.value.version === "string" ? parsed.schema.value.version : "1.0.0",
        template_version:
          typeof parsed.template.value.version === "string"
            ? parsed.template.value.version
            : "1.0.0",
      });
      const nextResult = {
        docId: documentResponse.doc_id,
        schemaId: schemaResponse.schema_id,
        templateId: templateResponse.template_id,
        taskId: taskResponse.task_id,
        status: taskResponse.status,
      };
      setResult(nextResult);
      onSelectionChange?.({
        docId: nextResult.docId,
        schemaId: nextResult.schemaId,
        templateId: nextResult.templateId,
        taskId: nextResult.taskId,
        taskStatus: nextResult.status,
      });
      onToast?.({
        tone: "success",
        title: "Task created",
        detail: nextResult.taskId,
      });
    } catch (error) {
      onToast?.({
        tone: "danger",
        title: "Import failed",
        detail: error instanceof Error ? error.message : "Unexpected import failure.",
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="document-panel import-page" aria-labelledby="import-page-title">
      <div className="document-panel__header">
        <div>
          <span className="section-label">Phase 8 setup</span>
          <h2 id="import-page-title">Import and setup</h2>
          <p>Load documents and contracts, then create a conversion task against the real API.</p>
        </div>
        <div className="button-row">
          <button
            className={`secondary-button ${activeDemo === "general" ? "secondary-button--active" : ""}`}
            onClick={() => loadDemo("general")}
            type="button"
          >
            <RotateCcw aria-hidden="true" size={15} />
            Load general demo
          </button>
          <button
            className={`secondary-button ${activeDemo === "policy" ? "secondary-button--active" : ""}`}
            onClick={() => loadDemo("policy")}
            type="button"
          >
            <Database aria-hidden="true" size={15} />
            Load policy demo
          </button>
        </div>
      </div>

      <div className="json-grid">
        {(Object.keys(PANEL_COPY) as ResourceKey[]).map((key) => (
          <JsonWorkbench
            description={PANEL_COPY[key].description}
            error={parsed[key].error}
            id={`json-${key}`}
            key={key}
            onChange={(value) => {
              setTexts((current) => ({ ...current, [key]: value }));
              setResult(null);
            }}
            title={PANEL_COPY[key].title}
            value={texts[key]}
          />
        ))}
      </div>

      <div className="action-strip">
        <div>
          <strong>{hasErrors ? "JSON validation blocked" : "Ready to create task"}</strong>
          <span>
            {hasErrors
              ? "Resolve parser errors above before calling the backend."
              : "The next action imports all three resources and creates a task."}
          </span>
        </div>
        <button
          className="primary-button"
          disabled={isSubmitting || hasErrors}
          onClick={handleCreateTask}
          type="button"
        >
          <Play aria-hidden="true" size={16} />
          {isSubmitting ? "Creating..." : "Create task"}
        </button>
      </div>

      {result ? (
        <div className="result-strip" role="status">
          <CheckCircle2 aria-hidden="true" size={18} />
          <span>Task {result.taskId}</span>
          <span>Doc {result.docId}</span>
          <span>Schema {result.schemaId}</span>
          <span>Template {result.templateId}</span>
          <span>Status {result.status}</span>
        </div>
      ) : null}
    </section>
  );
}
