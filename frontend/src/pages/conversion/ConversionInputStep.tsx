import { useState } from "react";

import { ExternalUirPanel } from "../../components/ExternalUirPanel";
import { sampleUirText } from "../../sampleUir";
import type { ExternalUirImportResponse, ExternalUirRouteReport } from "../../types";
import type { UirDocumentInput, UirValidationResult } from "./uirValidation";

type InputTab = "paste" | "external" | "example";

type ConversionInputStepProps = {
  text: string;
  validation: UirValidationResult | null;
  importedDocId: string;
  working: boolean;
  onTextChange: (value: string) => void;
  onExternalStandardPreview: (value: string) => void;
  onValidate: () => void;
  onImport: (document: UirDocumentInput) => Promise<void>;
  onExternalImported: (response: ExternalUirImportResponse) => void;
  onRecommendedRoute: (route: ExternalUirRouteReport) => void;
  onRouteConfirmationChange: (confirmed: boolean) => void;
};

export function ConversionInputStep({
  text,
  validation,
  importedDocId,
  working,
  onTextChange,
  onExternalStandardPreview,
  onValidate,
  onImport,
  onExternalImported,
  onRecommendedRoute,
  onRouteConfirmationChange
}: ConversionInputStepProps) {
  const [tab, setTab] = useState<InputTab>("external");
  const [lineWrap, setLineWrap] = useState(true);
  const [message, setMessage] = useState("");
  const document = validation?.valid ? validation.document : null;

  function formatJson() {
    try {
      onTextChange(JSON.stringify(JSON.parse(text), null, 2));
      setMessage("JSON 已格式化。"
      );
    } catch {
      setMessage("无法格式化：JSON 格式无效。"
      );
    }
  }

  async function copyJson() {
    try {
      await navigator.clipboard.writeText(text);
      setMessage("JSON 已复制。"
      );
    } catch {
      setMessage("浏览器未允许复制，请手动复制 JSON。"
      );
    }
  }

  async function importNormalUir() {
    if (!document) {
      setMessage("请先通过 UIR 校验。"
      );
      return;
    }
    try {
      await onImport(document);
      setMessage("UIR 已导入，可继续下一步。"
      );
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "UIR 导入失败。"
      );
    }
  }

  return (
    <section className="conversion-step-panel" aria-labelledby="conversion-input-title">
      <header className="conversion-step-header">
        <p>步骤 1</p>
        <h1 id="conversion-input-title">输入 UIR</h1>
        <p>粘贴标准 UIR，或使用 External UIR 适配后导入。</p>
      </header>

      <div className="conversion-input-tabs" role="tablist" aria-label="输入方式">
        <button
          id="conversion-tab-paste"
          type="button"
          role="tab"
          aria-selected={tab === "paste"}
          aria-controls="conversion-panel-paste"
          onClick={() => setTab("paste")}
        >
          粘贴 UIR
        </button>
        <button
          id="conversion-tab-external"
          type="button"
          role="tab"
          aria-selected={tab === "external"}
          aria-controls="conversion-panel-external"
          onClick={() => setTab("external")}
        >
          External UIR
        </button>
        <button
          id="conversion-tab-example"
          type="button"
          role="tab"
          aria-selected={tab === "example"}
          aria-controls="conversion-panel-example"
          onClick={() => setTab("example")}
        >
          示例
        </button>
      </div>

      {tab === "external" ? (
        <div id="conversion-panel-external" role="tabpanel" aria-labelledby="conversion-tab-external">
          <ExternalUirPanel
            currentDocId={importedDocId}
            working={working}
            onStandardUirPreview={onExternalStandardPreview}
            onImported={onExternalImported}
            onRecommendedRoute={onRecommendedRoute}
            onRouteConfirmationChange={onRouteConfirmationChange}
          />
        </div>
      ) : null}

      {tab === "paste" ? (
        <div id="conversion-panel-paste" role="tabpanel" aria-labelledby="conversion-tab-paste">
          <div className="conversion-input-toolbar" aria-label="JSON 操作">
            <button type="button" onClick={formatJson}>格式化 JSON</button>
            <button type="button" onClick={() => void copyJson()}>复制 JSON</button>
            <button type="button" onClick={() => onTextChange("")}>清空</button>
            <label>
              <input
                type="checkbox"
                checked={lineWrap}
                onChange={(event) => setLineWrap(event.target.checked)}
              />
              自动换行
            </label>
          </div>
          <textarea
            className="conversion-json-editor"
            aria-label="UIR JSON"
            value={text}
            onChange={(event) => onTextChange(event.target.value)}
            wrap={lineWrap ? "soft" : "off"}
            spellCheck={false}
            placeholder='{"doc_id":"doc-001","blocks":[]}'
          />
          <div className="conversion-input-actions">
            <button type="button" onClick={onValidate}>校验 UIR</button>
            <button type="button" className="conversion-primary-action" disabled={!document || working} onClick={() => void importNormalUir()}>
              导入 UIR
            </button>
          </div>
        </div>
      ) : null}

      {tab === "example" ? (
        <div id="conversion-panel-example" role="tabpanel" aria-labelledby="conversion-tab-example">
          <p>示例只会填入编辑器，不会自动导入或选择 SchemaPack。</p>
          <button type="button" onClick={() => onTextChange(sampleUirText)}>使用示例 UIR</button>
          <pre className="conversion-example-preview">{sampleUirText}</pre>
        </div>
      ) : null}

      {validation ? (
        <p className="conversion-validation-message" role={validation.valid ? "status" : "alert"}>
          {validation.valid ? `UIR 校验通过：${validation.document.doc_id}` : validation.error}
        </p>
      ) : null}
      {message ? <p className="conversion-input-message" role="status">{message}</p> : null}

      {document ? <DocumentPreview document={document} /> : null}
    </section>
  );
}

function DocumentPreview({ document }: { document: UirDocumentInput }) {
  const metadata = document.metadata;
  const title = typeof metadata === "object" && metadata && "title" in metadata
    ? String((metadata as Record<string, unknown>).title ?? "-")
    : "-";

  return (
    <section className="conversion-document-preview" aria-labelledby="conversion-document-preview-title">
      <h2 id="conversion-document-preview-title">文档概览</h2>
      <dl>
        <div><dt>doc_id</dt><dd>{document.doc_id}</dd></div>
        <div><dt>标题</dt><dd>{title}</dd></div>
        <div><dt>区块数</dt><dd>{document.blocks.length}</dd></div>
      </dl>
      <h3>来源区块预览</h3>
      <ol>
        {document.blocks.slice(0, 3).map((block, index) => {
          const value = block && typeof block === "object" ? block as Record<string, unknown> : {};
          return (
            <li key={String(value.block_id ?? index)}>
              <strong>{String(value.block_id ?? `block-${index + 1}`)}</strong>
              <span>{String(value.text ?? value.type ?? "无文本内容")}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
