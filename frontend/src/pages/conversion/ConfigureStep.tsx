import type { ChangeEvent } from "react";

import type { ContentOrganizationOptions } from "../../types";

export const defaultContentOrganizationOptions: ContentOrganizationOptions = {
  chunk_strategy: "source_block_aware",
  target_tokens: 768,
  min_tokens: 256,
  max_tokens: 1200,
  overlap_tokens: 80,
  protect_tables: true,
  protect_lists: true,
  protect_code_blocks: true,
  enable_parent_child: false,
  enable_light_semantic_boundary: true,
  summary_mode: "deterministic",
  keyword_mode: "deterministic"
};

type NumericOption = "target_tokens" | "min_tokens" | "max_tokens" | "overlap_tokens";
type BooleanOption = "protect_tables" | "protect_lists" | "protect_code_blocks" | "enable_parent_child" | "enable_light_semantic_boundary";

type ConfigureStepProps = {
  options: ContentOrganizationOptions;
  onChange: (options: ContentOrganizationOptions) => void;
};

export function ConfigureStep({ options, onChange }: ConfigureStepProps) {
  function setNumber(field: NumericOption) {
    return (event: ChangeEvent<HTMLInputElement>) => {
      const value = Number(event.target.value);
      if (Number.isFinite(value)) {
        onChange({ ...options, [field]: value });
      }
    };
  }

  function setBoolean(field: BooleanOption) {
    return (event: ChangeEvent<HTMLInputElement>) => {
      onChange({ ...options, [field]: event.target.checked });
    };
  }

  return (
    <section className="conversion-step-panel" aria-labelledby="conversion-configure-title">
      <header className="conversion-step-header">
        <p>步骤 3</p>
        <h1 id="conversion-configure-title">配置转换</h1>
        <p>配置已有的 ContentOrganizationOptions，不声明未提供的 provider 能力。</p>
      </header>

      <div className="conversion-config-grid">
        <label>
          <span>Chunk 策略</span>
          <select
            value={options.chunk_strategy}
            onChange={(event) => onChange({ ...options, chunk_strategy: event.target.value as ContentOrganizationOptions["chunk_strategy"] })}
          >
            <option value="fixed_window">固定窗口</option>
            <option value="heading_aware">按标题感知</option>
            <option value="source_block_aware">按来源区块感知</option>
            <option value="table_protect">表格保护</option>
            <option value="parent_child">父子 Chunk</option>
          </select>
        </label>
        <NumberField label="目标 Token" value={options.target_tokens} onChange={setNumber("target_tokens")} />
        <label>
          <span>摘要模式</span>
          <select
            value={options.summary_mode}
            onChange={(event) => onChange({ ...options, summary_mode: event.target.value as ContentOrganizationOptions["summary_mode"] })}
          >
            <option value="none">不生成</option>
            <option value="deterministic">确定性摘要</option>
          </select>
        </label>
        <label>
          <span>关键词模式</span>
          <select
            value={options.keyword_mode}
            onChange={(event) => onChange({ ...options, keyword_mode: event.target.value as ContentOrganizationOptions["keyword_mode"] })}
          >
            <option value="none">不生成</option>
            <option value="deterministic">确定性关键词</option>
          </select>
        </label>
      </div>

      <fieldset className="conversion-protection-options">
        <legend>内容保护</legend>
        <label><input type="checkbox" checked={options.protect_tables} onChange={setBoolean("protect_tables")} />保护表格</label>
        <label><input type="checkbox" checked={options.protect_lists} onChange={setBoolean("protect_lists")} />保护列表</label>
        <label><input type="checkbox" checked={options.protect_code_blocks} onChange={setBoolean("protect_code_blocks")} />保护代码区块</label>
      </fieldset>

      <details className="conversion-advanced-options">
        <summary>高级配置</summary>
        <div className="conversion-config-grid">
          <NumberField label="最小 Token" value={options.min_tokens} onChange={setNumber("min_tokens")} />
          <NumberField label="最大 Token" value={options.max_tokens} onChange={setNumber("max_tokens")} />
          <NumberField label="重叠 Token" value={options.overlap_tokens} onChange={setNumber("overlap_tokens")} />
        </div>
        <label><input type="checkbox" checked={options.enable_parent_child} onChange={setBoolean("enable_parent_child")} />启用父子 Chunk</label>
        <label><input type="checkbox" checked={options.enable_light_semantic_boundary} onChange={setBoolean("enable_light_semantic_boundary")} />启用轻量语义边界</label>
      </details>

      <section className="conversion-config-summary" aria-labelledby="conversion-config-summary-title">
        <h2 id="conversion-config-summary-title">配置摘要</h2>
        <dl>
          <div><dt>Chunk 策略</dt><dd>{options.chunk_strategy}</dd></div>
          <div><dt>Token 范围</dt><dd>{options.min_tokens} / {options.target_tokens} / {options.max_tokens}</dd></div>
          <div><dt>重叠 Token</dt><dd>{options.overlap_tokens}</dd></div>
          <div><dt>内容保护</dt><dd>{[options.protect_tables && "表格", options.protect_lists && "列表", options.protect_code_blocks && "代码区块"].filter(Boolean).join("、") || "无"}</dd></div>
        </dl>
      </section>
    </section>
  );
}

function NumberField({
  label,
  value,
  onChange
}: {
  label: string;
  value: number;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <label>
      <span>{label}</span>
      <input type="number" min="0" value={value} onChange={onChange} />
    </label>
  );
}
