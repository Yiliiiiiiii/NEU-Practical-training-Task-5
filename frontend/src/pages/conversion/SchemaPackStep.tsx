import type { ExternalUirRouteReport, MappingTemplate, TargetSchema } from "../../types";

export type SchemaPackSelection = {
  schema: TargetSchema;
  template: MappingTemplate;
};

type SchemaPackStepProps = {
  schemas: TargetSchema[];
  templates: MappingTemplate[];
  selected: SchemaPackSelection | null;
  recommendation: ExternalUirRouteReport | null;
  loading: boolean;
  error: string;
  onSelect: (selection: SchemaPackSelection) => void;
};

export function SchemaPackStep({
  schemas,
  templates,
  selected,
  recommendation,
  loading,
  error,
  onSelect
}: SchemaPackStepProps) {
  const packs = schemas.flatMap((schema) =>
    templates
      .filter((template) => template.schema_id === schema.schema_id)
      .map((template) => ({ schema, template }))
  );

  return (
    <section className="conversion-step-panel" aria-labelledby="conversion-schema-pack-title">
      <header className="conversion-step-header">
        <p>步骤 2</p>
        <h1 id="conversion-schema-pack-title">选择 SchemaPack</h1>
        <p>Schema 与映射模板成对选择；建议不会自动采纳。</p>
      </header>

      <RecommendationEvidence recommendation={recommendation} />

      {loading ? <p className="conversion-loading" role="status">正在加载 SchemaPack 目录。</p> : null}
      {error ? <p className="conversion-error" role="alert">{error}</p> : null}
      {!loading && !error && !packs.length ? (
        <p className="conversion-empty">当前目录中没有可配对的 SchemaPack。</p>
      ) : null}

      <div className="conversion-schema-pack-list" role="radiogroup" aria-label="SchemaPack 列表">
        {packs.map(({ schema, template }) => {
          const id = `${schema.schema_id}/${template.template_id}`;
          const archived = schema.status === "archived" || template.status === "archived";
          const chosen = selected?.schema.schema_id === schema.schema_id && selected.template.template_id === template.template_id;
          const aliases = Object.entries(template.aliases ?? {});

          return (
            <article key={id} className="conversion-schema-pack">
              <button
                type="button"
                role="radio"
                aria-checked={chosen}
                disabled={archived}
                onClick={() => onSelect({ schema, template })}
              >
                <span>{schema.name}</span>
                <strong>{template.name}</strong>
                <small>{archived ? "已归档，不可选择" : chosen ? "已选择" : "选择此 SchemaPack"}</small>
              </button>
              <dl>
                <div><dt>Schema 版本</dt><dd>{schema.version}</dd></div>
                <div><dt>模板版本</dt><dd>{template.version}</dd></div>
                <div><dt>状态</dt><dd>{archived ? "已归档" : schema.status ?? template.status ?? "可用"}</dd></div>
              </dl>
              <p>
                必填字段：{schema.fields?.filter((field) => field.required).map((field) => field.display_name || field.name).join("、") || "未声明"}
              </p>
              <p>
                别名：{aliases.length ? aliases.map(([field, values]) => `${field} (${values.join("、")})`).join("；") : "未声明"}
              </p>
              <details>
                <summary>查看配置</summary>
                <pre>{JSON.stringify({ schema, template }, null, 2)}</pre>
              </details>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function RecommendationEvidence({ recommendation }: { recommendation: ExternalUirRouteReport | null }) {
  if (!recommendation) {
    return (
      <section className="conversion-recommendation" aria-label="SchemaPack 建议">
        <h2>SchemaPack 建议</h2>
        <p>尚无路由建议，请根据文档语义人工选择。</p>
      </section>
    );
  }

  return (
    <section className="conversion-recommendation" aria-label="SchemaPack 建议证据">
      <h2>SchemaPack 建议证据</h2>
      <p>路由建议仅供选择，未自动采纳。</p>
      <p>
        {recommendation.selected_schema_id ?? "未选择"} / {recommendation.selected_template_id ?? "-"}，置信度 {Math.round(recommendation.confidence * 100)}%
      </p>
      <ul>
        {recommendation.candidates.slice(0, 3).flatMap((candidate) =>
          candidate.evidence.slice(0, 2).map((evidence, index) => (
            <li key={`${candidate.schema_id}-${evidence.value}-${index}`}>
              {evidence.evidence_type}: {evidence.value} ({evidence.source_path ?? "adapter"})
            </li>
          ))
        )}
      </ul>
    </section>
  );
}
