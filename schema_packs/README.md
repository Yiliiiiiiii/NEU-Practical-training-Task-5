# SchemaPack 配置说明

SchemaPack 是课题 5 转换智能体的外部输入配置资产，不是系统硬编码能力。

每个 SchemaPack 至少包含：

- `target_schema.json`：目标数据结构。
- `metadata_template.json`：文档级元数据模板。
- `mapping_rules.yaml`：字段别名、正则、合并、拆分、默认值、类型转换、负例规则。
- `content_org.yaml`：分段、打标、摘要、关键词、原文回链参数。
- `router_rules.yaml`：可选，用于从 UIR 推荐该 SchemaPack；不影响用户显式传入目标 Schema。

系统本体支持两种使用方式：

1. 直接传入 inline config：UIR + target_schema + metadata_template + mapping_rules + content_org。
2. 引用已注册 SchemaPack：UIR + schema_pack_id。

examples/ 下的 policy_doc、meeting_doc、procurement_doc、contract_doc、general_doc、announcement_doc 都只是示例配置与评测基准，不代表系统只能处理这些文档类型。

输入为 UIR + Target Schema + Metadata Template + Mapping Rules + Content Organization Config。

SchemaPack 只是示例配置与评测基准，不是系统能力边界。
