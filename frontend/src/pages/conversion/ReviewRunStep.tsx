import type { ContentOrganizationOptions } from "../../types";
import type { SchemaPackSelection } from "./SchemaPackStep";
import type { UirValidationResult } from "./uirValidation";

type ReviewRunStepProps = {
  validation: UirValidationResult | null;
  importedDocId: string;
  schemaPack: SchemaPackSelection | null;
  options: ContentOrganizationOptions;
  warnings: string[];
  working: boolean;
  message: string;
  onRun: () => void;
};

const plannedArtifacts = [
  "canonical.json",
  "content.json",
  "chunks.jsonl",
  "content_organization_report.json",
  "manifest.json"
];

export function ReviewRunStep({
  validation,
  importedDocId,
  schemaPack,
  options,
  warnings,
  working,
  message,
  onRun
}: ReviewRunStepProps) {
  const inputId = importedDocId || (validation?.valid ? validation.document.doc_id : "未导入");

  return (
    <section className="conversion-step-panel" aria-labelledby="conversion-review-title">
      <header className="conversion-step-header">
        <p>步骤 4</p>
        <h1 id="conversion-review-title">复核并运行</h1>
        <p>运行时会按需要导入标准 UIR、创建任务并执行任务。</p>
      </header>

      <section className="conversion-review-section" aria-labelledby="conversion-review-input-title">
        <h2 id="conversion-review-input-title">输入复核</h2>
        <dl>
          <div><dt>doc_id</dt><dd>{inputId}</dd></div>
          <div><dt>区块数</dt><dd>{validation?.valid ? validation.document.blocks.length : "由 External UIR 导入结果确定"}</dd></div>
          <div><dt>状态</dt><dd>{importedDocId ? "已导入" : validation?.valid ? "已校验，运行时导入" : "未就绪"}</dd></div>
        </dl>
      </section>

      <section className="conversion-review-section" aria-labelledby="conversion-review-schema-title">
        <h2 id="conversion-review-schema-title">SchemaPack 复核</h2>
        <dl>
          <div><dt>Schema</dt><dd>{schemaPack?.schema.schema_id ?? "未选择"}</dd></div>
          <div><dt>模板</dt><dd>{schemaPack?.template.template_id ?? "未选择"}</dd></div>
          <div><dt>版本</dt><dd>{schemaPack ? `${schemaPack.schema.version} / ${schemaPack.template.version}` : "-"}</dd></div>
        </dl>
      </section>

      <section className="conversion-review-section" aria-labelledby="conversion-review-config-title">
        <h2 id="conversion-review-config-title">配置复核</h2>
        <p>
          {options.chunk_strategy}，目标 {options.target_tokens} Token，重叠 {options.overlap_tokens} Token，
          {options.summary_mode === "deterministic" ? "确定性摘要" : "不生成摘要"}。
        </p>
      </section>

      <section className="conversion-review-section" aria-labelledby="conversion-review-warning-title">
        <h2 id="conversion-review-warning-title">警告复核</h2>
        {warnings.length ? <ul>{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : <p>没有待处理警告。</p>}
      </section>

      <section className="conversion-review-section" aria-labelledby="conversion-review-artifacts-title">
        <h2 id="conversion-review-artifacts-title">预期产物</h2>
        <ul>{plannedArtifacts.map((artifact) => <li key={artifact}>{artifact}</li>)}</ul>
      </section>

      {message ? <p className="conversion-run-message" role="status">{message}</p> : null}
      <button type="button" className="conversion-primary-action" disabled={working || !schemaPack} onClick={onRun}>
        {working ? "正在运行转换" : "运行转换"}
      </button>
    </section>
  );
}
