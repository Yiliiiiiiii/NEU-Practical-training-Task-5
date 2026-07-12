import {
  FileDown,
  Files,
  FlaskConical,
  Search,
  ShieldCheck
} from "lucide-react";
import { useState } from "react";

import { api } from "../api";
import { parseSchemaDraftSamples } from "../schemaDraftSamples";
import type {
  SchemaDraftDiscovery,
  SchemaDraftExportResponse,
  SchemaDraftPackage
} from "../types";

export function SchemaDraftLabPanel() {
  const [sampleText, setSampleText] = useState("[]");
  const [schemaId, setSchemaId] = useState("candidate_doc");
  const [schemaName, setSchemaName] = useState("候选文档草案");
  const [templateId, setTemplateId] = useState("candidate_doc_draft_v1");
  const [discovery, setDiscovery] = useState<SchemaDraftDiscovery | null>(null);
  const [draftPackage, setDraftPackage] = useState<SchemaDraftPackage | null>(null);
  const [exported, setExported] = useState<SchemaDraftExportResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "working" | "ready" | "error">("idle");
  const [message, setMessage] = useState("");

  async function discover() {
    await runAction(async () => {
      const result = await api.discoverSchemaDraftFields(
        parseSchemaDraftSamples(sampleText)
      );
      setDiscovery(result);
      setMessage(`已发现 ${result.field_candidates.length} 个字段候选项。`);
    });
  }

  async function generate() {
    await runAction(async () => {
      const result = await api.generateSchemaDraft({
        documents: parseSchemaDraftSamples(sampleText),
        schema_id: schemaId,
        schema_name: schemaName,
        template_id: templateId
      });
      setDiscovery(result.discovery);
      setDraftPackage(result);
      setExported(null);
      setMessage(`草案 ${result.draft_id} 已生成，等待复核。`);
    });
  }

  async function validate() {
    if (!draftPackage) {
      return;
    }
    await runAction(async () => {
      const riskReport = await api.validateSchemaDraft(draftPackage.draft_id);
      setDraftPackage({ ...draftPackage, risk_report: riskReport });
      setMessage(`风险扫描完成，发现 ${riskReport.risk_count} 项。`);
    });
  }

  async function exportDraft() {
    if (!draftPackage) {
      return;
    }
    await runAction(async () => {
      const result = await api.exportSchemaDraft(draftPackage.draft_id);
      setExported(result);
      setMessage("草案产物已导出。");
    });
  }

  async function onFilesSelected(files: FileList | null) {
    if (!files?.length) {
      return;
    }
    const values = await Promise.all(
      Array.from(files).map(async (file) => JSON.parse(await file.text()))
    );
    const documents = values.flatMap((value) => (Array.isArray(value) ? value : [value]));
    setSampleText(JSON.stringify(documents, null, 2));
    setMessage(`已加载 ${documents.length} 个样本文档。`);
  }

  async function runAction(action: () => Promise<void>) {
    setStatus("working");
    setMessage("");
    try {
      await action();
      setStatus("ready");
    } catch (caught) {
      setStatus("error");
      setMessage(caught instanceof Error ? caught.message : "Schema 草案操作失败。");
    }
  }

  return (
    <section className="schema-draft-panel" aria-label="Schema Draft 实验室">
      <div className="schema-draft-head">
        <div>
          <h3>Schema Draft 实验室</h3>
          <p>字段发现与受治理的草案产物。</p>
        </div>
        <FlaskConical size={18} />
      </div>

      <div className="schema-draft-governance">
        <ShieldCheck size={16} />
        <span>草案绝不会自动激活，必须经过目录复核。</span>
      </div>

      <div className="schema-draft-grid">
        <label className="control-group">
          <span>Schema ID</span>
          <input value={schemaId} onChange={(event) => setSchemaId(event.target.value)} />
        </label>
        <label className="control-group">
          <span>模板 ID</span>
          <input
            value={templateId}
            onChange={(event) => setTemplateId(event.target.value)}
          />
        </label>
      </div>
      <label className="control-group">
        <span>草案名称</span>
        <input value={schemaName} onChange={(event) => setSchemaName(event.target.value)} />
      </label>

      <label className="file-button" htmlFor="schema-draft-files">
        <Files size={16} />
        加载 UIR 样本
      </label>
      <input
        id="schema-draft-files"
        className="visually-hidden-input"
        type="file"
        accept="application/json,.json"
        multiple
        onChange={(event) => void onFilesSelected(event.currentTarget.files)}
      />

      <textarea
        className="schema-draft-editor"
        aria-label="Schema 草案样本 JSON"
        value={sampleText}
        onChange={(event) => setSampleText(event.target.value)}
        spellCheck={false}
      />

      <div className="schema-draft-actions">
        <button type="button" onClick={() => void discover()} disabled={status === "working"}>
          <Search size={16} />
          发现字段
        </button>
        <button
          type="button"
          className="primary"
          onClick={() => void generate()}
          disabled={status === "working"}
        >
          <FlaskConical size={16} />
          生成草案
        </button>
        <button
          type="button"
          onClick={() => void validate()}
          disabled={status === "working" || !draftPackage}
        >
          <ShieldCheck size={16} />
          验证
        </button>
        <button
          type="button"
          onClick={() => void exportDraft()}
          disabled={status === "working" || !draftPackage}
        >
          <FileDown size={16} />
          导出
        </button>
      </div>

      {message ? <p className={`external-message external-${status}`}>{message}</p> : null}

      {discovery ? (
        <div className="schema-draft-results">
          <div className="schema-draft-metrics">
            <span>样本</span>
            <strong>{discovery.sample_count}</strong>
            <span>候选项</span>
            <strong>{discovery.field_candidates.length}</strong>
            <span>自动采纳</span>
            <strong>{discovery.llm_auto_accepted_count}</strong>
          </div>
          <div className="schema-draft-fields">
            {discovery.field_candidates.slice(0, 8).map((field) => (
              <div key={field.field_name}>
                <strong>{field.field_name}</strong>
                <em>{Math.round(field.frequency * 100)}%</em>
                <span>{field.source_labels.join(", ")}</span>
                {field.review_required ? <small>需要复核</small> : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {draftPackage ? (
        <div className="schema-draft-status">
          <span>草案</span>
          <strong>{draftPackage.draft_id}</strong>
          <em>{draftPackage.risk_report.risk_count} 项风险</em>
          <small>不得自动激活</small>
        </div>
      ) : null}

      {exported ? (
        <details className="json-details schema-draft-export">
          <summary>已导出的产物</summary>
          <pre>{JSON.stringify(exported, null, 2)}</pre>
        </details>
      ) : null}
    </section>
  );
}
