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
  const [schemaName, setSchemaName] = useState("Candidate Document Draft");
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
      setMessage(`Discovered ${result.field_candidates.length} field candidates.`);
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
      setMessage(`Draft ${result.draft_id} generated for review.`);
    });
  }

  async function validate() {
    if (!draftPackage) {
      return;
    }
    await runAction(async () => {
      const riskReport = await api.validateSchemaDraft(draftPackage.draft_id);
      setDraftPackage({ ...draftPackage, risk_report: riskReport });
      setMessage(`Risk scan completed with ${riskReport.risk_count} findings.`);
    });
  }

  async function exportDraft() {
    if (!draftPackage) {
      return;
    }
    await runAction(async () => {
      const result = await api.exportSchemaDraft(draftPackage.draft_id);
      setExported(result);
      setMessage("Draft artifacts exported.");
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
    setMessage(`${documents.length} sample documents loaded.`);
  }

  async function runAction(action: () => Promise<void>) {
    setStatus("working");
    setMessage("");
    try {
      await action();
      setStatus("ready");
    } catch (caught) {
      setStatus("error");
      setMessage(caught instanceof Error ? caught.message : "Schema draft operation failed.");
    }
  }

  return (
    <section className="schema-draft-panel" aria-label="Schema Draft Lab">
      <div className="schema-draft-head">
        <div>
          <h3>Schema Draft Lab</h3>
          <p>Field discovery and governed draft artifacts.</p>
        </div>
        <FlaskConical size={18} />
      </div>

      <div className="schema-draft-governance">
        <ShieldCheck size={16} />
        <span>Drafts never activate automatically. Catalog review is required.</span>
      </div>

      <div className="schema-draft-grid">
        <label className="control-group">
          <span>Schema ID</span>
          <input value={schemaId} onChange={(event) => setSchemaId(event.target.value)} />
        </label>
        <label className="control-group">
          <span>Template ID</span>
          <input
            value={templateId}
            onChange={(event) => setTemplateId(event.target.value)}
          />
        </label>
      </div>
      <label className="control-group">
        <span>Draft Name</span>
        <input value={schemaName} onChange={(event) => setSchemaName(event.target.value)} />
      </label>

      <label className="file-button" htmlFor="schema-draft-files">
        <Files size={16} />
        Load UIR Samples
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
        aria-label="Schema draft sample JSON"
        value={sampleText}
        onChange={(event) => setSampleText(event.target.value)}
        spellCheck={false}
      />

      <div className="schema-draft-actions">
        <button type="button" onClick={() => void discover()} disabled={status === "working"}>
          <Search size={16} />
          Discover
        </button>
        <button
          type="button"
          className="primary"
          onClick={() => void generate()}
          disabled={status === "working"}
        >
          <FlaskConical size={16} />
          Generate Draft
        </button>
        <button
          type="button"
          onClick={() => void validate()}
          disabled={status === "working" || !draftPackage}
        >
          <ShieldCheck size={16} />
          Validate
        </button>
        <button
          type="button"
          onClick={() => void exportDraft()}
          disabled={status === "working" || !draftPackage}
        >
          <FileDown size={16} />
          Export
        </button>
      </div>

      {message ? <p className={`external-message external-${status}`}>{message}</p> : null}

      {discovery ? (
        <div className="schema-draft-results">
          <div className="schema-draft-metrics">
            <span>samples</span>
            <strong>{discovery.sample_count}</strong>
            <span>candidates</span>
            <strong>{discovery.field_candidates.length}</strong>
            <span>auto accepted</span>
            <strong>{discovery.llm_auto_accepted_count}</strong>
          </div>
          <div className="schema-draft-fields">
            {discovery.field_candidates.slice(0, 8).map((field) => (
              <div key={field.field_name}>
                <strong>{field.field_name}</strong>
                <em>{Math.round(field.frequency * 100)}%</em>
                <span>{field.source_labels.join(", ")}</span>
                {field.review_required ? <small>review required</small> : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {draftPackage ? (
        <div className="schema-draft-status">
          <span>draft</span>
          <strong>{draftPackage.draft_id}</strong>
          <em>{draftPackage.risk_report.risk_count} risks</em>
          <small>must not auto activate</small>
        </div>
      ) : null}

      {exported ? (
        <details className="json-details schema-draft-export">
          <summary>Exported artifacts</summary>
          <pre>{JSON.stringify(exported, null, 2)}</pre>
        </details>
      ) : null}
    </section>
  );
}
