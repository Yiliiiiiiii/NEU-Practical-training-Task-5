import { useEffect, useMemo, useState } from "react";

import { api } from "../../api";
import { navigate } from "../../app/router";
import { WorkflowLayout } from "../../layouts/WorkflowLayout";
import type {
  ContentOrganizationOptions,
  ExternalUirImportResponse,
  ExternalUirRouteReport,
  MappingTemplate,
  TargetSchema
} from "../../types";
import { ConfigureStep, defaultContentOrganizationOptions } from "./ConfigureStep";
import { ConversionInputStep } from "./ConversionInputStep";
import { ReviewRunStep } from "./ReviewRunStep";
import { SchemaPackStep, type SchemaPackSelection } from "./SchemaPackStep";
import { validateUirText, type UirDocumentInput, type UirValidationResult } from "./uirValidation";

const recoveryKey = "schemapack-agent:conversion-recovery";

type BrowserRecovery = {
  uirText?: string;
  schemaId?: string;
  templateId?: string;
  options?: ContentOrganizationOptions;
};

function loadBrowserRecovery(): BrowserRecovery {
  try {
    const value = window.sessionStorage.getItem(recoveryKey);
    return value ? JSON.parse(value) as BrowserRecovery : {};
  } catch {
    return {};
  }
}

export function ConversionPage() {
  const [recovery] = useState(loadBrowserRecovery);
  const [step, setStep] = useState(1);
  const [uirText, setUirText] = useState(() => recovery.uirText ?? "");
  const [inputKind, setInputKind] = useState<"standard" | "external">("standard");
  const [validation, setValidation] = useState<UirValidationResult | null>(null);
  const [importedDocId, setImportedDocId] = useState("");
  const [externalRoute, setExternalRoute] = useState<ExternalUirRouteReport | null>(null);
  const [externalRouteConfirmed, setExternalRouteConfirmed] = useState(false);
  const [externalWarnings, setExternalWarnings] = useState<string[]>([]);
  const [schemas, setSchemas] = useState<TargetSchema[]>([]);
  const [templates, setTemplates] = useState<MappingTemplate[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState("");
  const [schemaPack, setSchemaPack] = useState<SchemaPackSelection | null>(null);
  const [options, setOptions] = useState<ContentOrganizationOptions>(
    () => recovery.options ?? defaultContentOrganizationOptions
  );
  const [working, setWorking] = useState(false);
  const [runMessage, setRunMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    void Promise.all([api.listSchemas(), api.listTemplates()])
      .then(([schemaResponse, templateResponse]) => {
        if (cancelled) {
          return;
        }
        setSchemas(schemaResponse.items);
        setTemplates(templateResponse.items);
        setCatalogError("");
      })
      .catch((caught) => {
        if (!cancelled) {
          setCatalogError(caught instanceof Error ? caught.message : "SchemaPack 目录加载失败。"
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setCatalogLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (schemaPack || !recovery.schemaId || !recovery.templateId) {
      return;
    }
    const schema = schemas.find((item) => item.schema_id === recovery.schemaId);
    const template = templates.find((item) => item.template_id === recovery.templateId);
    if (schema && template && schema.status !== "archived" && template.status !== "archived") {
      setSchemaPack({ schema, template });
    }
  }, [recovery, schemaPack, schemas, templates]);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(
        recoveryKey,
        JSON.stringify({
          uirText,
          schemaId: schemaPack?.schema.schema_id,
          templateId: schemaPack?.template.template_id,
          options
        } satisfies BrowserRecovery)
      );
    } catch {
      // Browser-local recovery is optional when storage is unavailable.
    }
  }, [options, schemaPack, uirText]);

  const configError = useMemo(() => {
    if (options.min_tokens > options.target_tokens || options.target_tokens > options.max_tokens) {
      return "Token 范围必须满足最小值 <= 目标值 <= 最大值。";
    }
    if (options.overlap_tokens >= options.target_tokens) {
      return "重叠 Token 必须小于目标 Token。";
    }
    return "";
  }, [options]);

  const inputReady = inputKind === "external"
    ? Boolean(importedDocId && (!externalRoute?.review_required || externalRouteConfirmed))
    : Boolean(validation?.valid);
  const highestAvailableStep = !inputReady ? 1 : !schemaPack ? 2 : configError ? 3 : 4;
  const workflowWarnings = [
    ...externalWarnings,
    ...(configError ? [configError] : []),
    ...(externalRoute?.review_required && !externalRouteConfirmed ? ["External UIR 路由需要人工确认。"] : [])
  ];

  function updateUirText(value: string) {
    setInputKind("standard");
    setUirText(value);
    setValidation(null);
    setImportedDocId("");
    setExternalRoute(null);
    setExternalRouteConfirmed(false);
    setExternalWarnings([]);
    setRunMessage("");
  }

  function receiveExternalStandardPreview(value: string) {
    setInputKind("external");
    setUirText(value);
    setValidation(validateUirText(value));
    setImportedDocId("");
    setExternalRoute(null);
    setExternalRouteConfirmed(false);
    setExternalWarnings([]);
    setRunMessage("");
  }

  function validateInput() {
    setValidation(validateUirText(uirText));
    setRunMessage("");
  }

  async function importNormalUir(document: UirDocumentInput) {
    setWorking(true);
    try {
      const imported = await api.importDocument(document);
      setImportedDocId(imported.doc_id);
      setExternalRoute(null);
      setExternalRouteConfirmed(false);
    } finally {
      setWorking(false);
    }
  }

  function receiveExternalImport(response: ExternalUirImportResponse) {
    setImportedDocId(response.doc_id);
    setExternalWarnings(response.warnings);
    setRunMessage("");
  }

  function changeStep(nextStep: number) {
    if (nextStep >= 1 && nextStep <= highestAvailableStep) {
      setStep(nextStep);
    }
  }

  async function runConversion() {
    if (!schemaPack) {
      return;
    }
    setWorking(true);
    setRunMessage("正在准备转换任务。"
    );
    try {
      let docId = importedDocId;
      if (!docId) {
        if (!validation?.valid) {
          throw new Error("标准 UIR 尚未通过校验。"
          );
        }
        const imported = await api.importDocument(validation.document);
        docId = imported.doc_id;
        setImportedDocId(docId);
      }
      const created = await api.createTask({
        doc_id: docId,
        schema_id: schemaPack.schema.schema_id,
        template_id: schemaPack.template.template_id,
        options: { content_organization: options }
      });
      await api.executeTask(created.task_id);
      navigate(`/conversions/executing/${encodeURIComponent(created.task_id)}`);
    } catch (caught) {
      setRunMessage(caught instanceof Error ? caught.message : "转换运行失败。"
      );
    } finally {
      setWorking(false);
    }
  }

  const context = {
    input: importedDocId || (validation?.valid ? validation.document.doc_id : "尚未校验"),
    schemaPack: schemaPack ? `${schemaPack.schema.schema_id} / ${schemaPack.template.template_id}` : "尚未选择",
    configuration: `${options.chunk_strategy}，${options.target_tokens} Token`
  };

  return (
    <WorkflowLayout
      currentStep={step}
      context={context}
      onStepChange={changeStep}
      steps={[
        { index: 1, label: "输入 UIR", available: true },
        { index: 2, label: "选择 SchemaPack", available: highestAvailableStep >= 2 },
        { index: 3, label: "配置转换", available: highestAvailableStep >= 3 },
        { index: 4, label: "复核并运行", available: highestAvailableStep >= 4 }
      ]}
    >
      {step === 1 ? (
        <ConversionInputStep
          text={uirText}
          validation={validation}
          importedDocId={importedDocId}
          working={working}
          onTextChange={updateUirText}
          onExternalStandardPreview={receiveExternalStandardPreview}
          onValidate={validateInput}
          onImport={importNormalUir}
          onExternalImported={receiveExternalImport}
          onRecommendedRoute={setExternalRoute}
          onRouteConfirmationChange={setExternalRouteConfirmed}
        />
      ) : null}
      {step === 2 ? (
        <SchemaPackStep
          schemas={schemas}
          templates={templates}
          selected={schemaPack}
          recommendation={externalRoute}
          loading={catalogLoading}
          error={catalogError}
          onSelect={setSchemaPack}
        />
      ) : null}
      {step === 3 ? <ConfigureStep options={options} onChange={setOptions} /> : null}
      {step === 4 ? (
        <ReviewRunStep
          validation={validation}
          importedDocId={importedDocId}
          schemaPack={schemaPack}
          options={options}
          warnings={workflowWarnings}
          working={working}
          message={runMessage}
          onRun={() => void runConversion()}
        />
      ) : null}

      <nav className="conversion-step-actions" aria-label="步骤操作">
        <button type="button" onClick={() => changeStep(step - 1)} disabled={step === 1 || working}>上一步</button>
        {step < 4 ? (
          <button type="button" className="conversion-primary-action" onClick={() => changeStep(step + 1)} disabled={working || step >= highestAvailableStep}>
            下一步
          </button>
        ) : null}
      </nav>
      <p className="conversion-local-recovery">浏览器本地恢复（browser-local）：仅保存本地输入和选择，并非服务端草稿。</p>
    </WorkflowLayout>
  );
}
