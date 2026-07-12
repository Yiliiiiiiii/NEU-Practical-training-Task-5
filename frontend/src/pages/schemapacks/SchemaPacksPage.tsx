import { useEffect, useMemo, useState } from "react";

import { api } from "../../api";
import { PageState } from "../../components/feedback/PageState";
import { StatusBadge } from "../../components/status/StatusBadge";
import { DataTable } from "../../components/tables/DataTable";
import { SchemaDraftLabPanel } from "../../components/SchemaDraftLabPanel";
import type { MappingTemplate, TargetSchema } from "../../types";

type Tab = "catalog" | "draft";

function requiredCount(schema: TargetSchema) {
  return schema.fields ? schema.fields.filter((field) => field.required).length : null;
}

export function SchemaPacksPage() {
  const [tab, setTab] = useState<Tab>("catalog");
  const [schemas, setSchemas] = useState<TargetSchema[]>([]);
  const [templates, setTemplates] = useState<MappingTemplate[]>([]);
  const [selectedSchemaId, setSelectedSchemaId] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [schemaResult, templateResult] = await Promise.all([api.listSchemas(), api.listTemplates()]);
      setSchemas(schemaResult.items);
      setTemplates(templateResult.items);
      setSelectedSchemaId((current) => current || schemaResult.items[0]?.schema_id || "");
      setSelectedTemplateId((current) => current || templateResult.items[0]?.template_id || "");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "SchemaPack 目录读取失败。");
    } finally {
      setLoading(false);
    }
  }

  const selectedSchema = schemas.find((schema) => schema.schema_id === selectedSchemaId) ?? null;
  const selectedTemplate = templates.find((template) => template.template_id === selectedTemplateId) ?? null;
  const selectedSchemaTemplates = useMemo(
    () => templates.filter((template) => template.schema_id === selectedSchemaId),
    [selectedSchemaId, templates]
  );

  return (
    <section className="route-placeholder operations-page schemapacks-page" aria-labelledby="schemapacks-title">
      <p className="page-eyebrow">SchemaPacks</p>
      <h1 id="schemapacks-title">SchemaPacks 目录</h1>
      <p className="route-placeholder-description">
        Schema 与模板版本仅供查看；Schema Draft 必须经过目录复核，不会自动激活。
      </p>

      <div className="operations-tabs schemapacks-tabs" role="tablist" aria-label="SchemaPacks 页面">
        <button type="button" role="tab" aria-selected={tab === "catalog"} onClick={() => setTab("catalog")}>目录</button>
        <button type="button" role="tab" aria-selected={tab === "draft"} onClick={() => setTab("draft")}>Schema Draft 实验室</button>
      </div>

      {tab === "draft" ? <SchemaDraftLabPanel /> : null}
      {tab === "catalog" && loading ? <PageState kind="loading" title="正在读取 SchemaPacks" /> : null}
      {tab === "catalog" && error ? <PageState kind="error" title="SchemaPack 目录读取失败" detail={error} /> : null}
      {tab === "catalog" && !loading && !error && !schemas.length && !templates.length ? (
        <PageState kind="empty" title="暂无 SchemaPack" />
      ) : null}

      {tab === "catalog" && !loading && !error ? (
        <>
          <section className="operations-section schemapacks-schema-list" aria-labelledby="schemas-title">
            <h2 id="schemas-title">Schema</h2>
            <DataTable label="Schema 列表">
              <table>
                <thead><tr><th>Schema</th><th>版本</th><th>状态</th><th>必填字段</th></tr></thead>
                <tbody>
                  {schemas.map((schema) => (
                    <tr key={schema.schema_id}>
                      <td><button type="button" onClick={() => setSelectedSchemaId(schema.schema_id)}>{schema.name || schema.schema_id}</button></td>
                      <td>{schema.version}</td>
                      <td><StatusBadge status={schema.status ?? "unknown"} /></td>
                      <td>{requiredCount(schema) ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </DataTable>
          </section>

          <section className="operations-section schemapacks-template-list" aria-labelledby="templates-title">
            <h2 id="templates-title">映射模板</h2>
            <DataTable label="映射模板列表">
              <table>
                <thead><tr><th>模板</th><th>Schema</th><th>版本</th><th>状态</th></tr></thead>
                <tbody>
                  {templates.map((template) => (
                    <tr key={template.template_id}>
                      <td><button type="button" onClick={() => setSelectedTemplateId(template.template_id)}>{template.name || template.template_id}</button></td>
                      <td>{template.schema_id}</td>
                      <td>{template.version}</td>
                      <td><StatusBadge status={template.status ?? "unknown"} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </DataTable>
          </section>

          <section className="operations-section schemapacks-detail" aria-labelledby="schemapack-detail-title">
            <h2 id="schemapack-detail-title">目录详情</h2>
            {selectedSchema ? (
              <article>
                <h3>{selectedSchema.name || selectedSchema.schema_id}</h3>
                <p>Schema ID：{selectedSchema.schema_id}</p>
                <p>状态：{selectedSchema.status ?? "—"}</p>
                <p>必填字段：{requiredCount(selectedSchema) ?? "—"}</p>
                <p>{selectedSchema.description ?? "—"}</p>
                <details>
                  <summary>字段配置</summary>
                  <pre>{JSON.stringify(selectedSchema.fields ?? null, null, 2)}</pre>
                </details>
              </article>
            ) : <PageState kind="empty" title="未选择 Schema" />}
            {selectedTemplate ? (
              <article>
                <h3>{selectedTemplate.name || selectedTemplate.template_id}</h3>
                <p>模板 ID：{selectedTemplate.template_id}</p>
                <p>绑定 Schema：{selectedTemplate.schema_id}</p>
                <p>状态：{selectedTemplate.status ?? "—"}</p>
                <details>
                  <summary>映射配置</summary>
                  <pre>{JSON.stringify(selectedTemplate.aliases ?? null, null, 2)}</pre>
                </details>
              </article>
            ) : <PageState kind="empty" title="未选择映射模板" />}
            <p>所选 Schema 的模板数：{selectedSchemaId ? selectedSchemaTemplates.length : "—"}</p>
          </section>
        </>
      ) : null}
    </section>
  );
}
