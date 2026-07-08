# 课题 5 需求映射

本文档把课题 5 要求映射到当前 SchemaPack Agent 的实现和已提交证据。当前口径同步到 `main@7fd38c77`。

| Requirement | 当前实现 | 证据 |
| --- | --- | --- |
| Standardization | UIR import、schema/template snapshots、deterministic mapping、transform、canonical model、structured JSON、Markdown 和 package output。 | `mapping_report.json`、`transform_report.json`、`canonical.json`、`content.json`、`content.md`、[`docs/package_spec.md`](../package_spec.md) |
| Intelligent organization | 确定性 chunk strategies、summaries、keywords、content/management/quality tags、受保护 table/list/code chunks、parent-child metadata 和 source links。 | `content_organization_report.json`、`chunks.jsonl`、[`reports/content_organization_retrieval_eval.md`](../../reports/content_organization_retrieval_eval.md) |
| Specialized conversion | 5 个 seeded document catalog families，包括 `procurement_doc`、`general_doc`、`meeting_doc`、`policy_doc`、`contract_doc`。 | [`reports/procurement_doc_eval_report.md`](../../reports/procurement_doc_eval_report.md)、[`reports/real_world_dataset_inventory.json`](../../reports/real_world_dataset_inventory.json) |
| Evaluation | Production-like evaluator、60-document real-world corpus、Phase C/D non-procurement evaluators、Evaluation Center、metric registry、scorecard 与 regression gates。 | [`reports/real_world_eval_report.json`](../../reports/real_world_eval_report.json)、[`reports/phase_d_non_procurement_mapping_eval_report.json`](../../reports/phase_d_non_procurement_mapping_eval_report.json)、[`reports/evaluation_center`](../../reports/evaluation_center) |
| Continuous improvement | Review records、review-derived knowledge candidates、accepted/rejected candidate states、draft/active/archived knowledge packs 和 effective-template resolution。 | [`reports/review_knowledge_growth_report.json`](../../reports/review_knowledge_growth_report.json)、Review 与 Knowledge APIs |
| Safety and traceability | Mapping evidence、confidence tiers、review-required reasons、badcase filters、immutable task snapshots、SchemaPack-Lineage、manifest hashes、package verifier output、可选 API-key auth、audit logs 和 secret redaction。 | [`docs/api_usage_examples.md`](../api_usage_examples.md)、[`docs/lineage.md`](../lineage.md)、[`reports/secret_redaction_audit_report.json`](../../reports/secret_redaction_audit_report.json) |
| External UIR compatibility | block-list 与 section-tree 外部 UIR adapter，先转换为标准 `UIRDocument`，再由 Schema Router 推荐到现有 schema/template。 | [`docs/external_uir_integration.md`](../external_uir_integration.md)、[`reports/external_uir_adapter_eval_report.md`](../../reports/external_uir_adapter_eval_report.md) |
| Schema evolution | Field discovery、schema/template draft generation、风险检查、校验与显式导出；draft 不自动激活。 | [`reports/evaluation_center/schema_drafts.md`](../../reports/evaluation_center/schema_drafts.md)、[`docs/交接/project_status.md`](project_status.md) |
| Review governance | Review summary/grouping/impact preview、批量审批安全、负知识、knowledge pack conflict/diff/impact/rollback。 | [`docs/api_usage_examples.md`](../api_usage_examples.md)、[`docs/user_web_workbench_guide.md`](../user_web_workbench_guide.md) |
| Integration ecosystem | Package 1.1、RAG/training/CSV contracts、统一 CLI、Python SDK 与人工注册的 Adapter scaffold。 | [`contracts`](../../contracts)、[`sdk/python/README.md`](../../sdk/python/README.md)、[`templates/adapter_plugin/README.md`](../../templates/adapter_plugin/README.md) |
| Optional raw upstream | Docling/Unstructured 离线可选入口输出 External UIR；默认不安装 provider，不提供 OCR 或 raw-document API。 | [`examples/raw_upstream/README.md`](../../examples/raw_upstream/README.md)、[`docs/交接/project_status.md`](project_status.md) |
| LLM/DeepSeek safety | DeepSeek provider smoke 与 ablation 只进入 report-only/suggestion path；不自动接受 mapping，不激活 catalog，不产生生产规则。 | [`reports/deepseek_provider_smoke_report.json`](../../reports/deepseek_provider_smoke_report.json)、[`reports/deepseek_ablation_report.json`](../../reports/deepseek_ablation_report.json) |

## 当前证据摘要

- Unified verification：`backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi` 通过，包含 662 backend tests、Ruff clean、frontend production build success 和 63 OpenAPI paths。
- Frontend tests：24/24 passed。
- Real-world corpus：60 UIR、60 mapping gold、120 retrieval queries、66 badcases。
- Real-world pipeline：60/60 imports、60/60 executions、60/60 verifier-passing packages。
- Real-world mapping：overall recall `0.6831896552`、validation pass 40/60、package pass 60/60、badcase violations 0。
- Non-procurement semantic sprint：当前记录 50 samples，average recall `0.8063730159`，strict pass 47/50，required missing 2，review-required 16，package 50/50，badcase violations 0。
- UIR Quality Gate：60 total，12 pass，48 review，0 reject/unsupported。
- DeepSeek：provider smoke passed，suggestion_count 2，auto accepted 0，secret leaks 0。
- Review judge：979 pending reviewed in dry-run/apply-safe，suggest reject 26，suggest approve 0，applied 0。
- SchemaPack-Lineage：parse/field/chunk/artifact coverage 均为 1.0，broken edges、secret leaks、LLM auto accepted 均为 0。
- Regression gates：8/8 passed。

## 已实现边界

当前 runtime line：

```text
UIR -> Schema/Template Snapshot -> Candidate Extraction -> Mapping
-> Transform -> Canonical Model -> Render -> Content Organization
-> Validation -> Manifest -> ZIP -> Package Verification
```

项目实现了可选 API-key authentication、task/package audit logs、review governance、knowledge-pack activation 和 local/container deployment profiles。这些是轻量项目控制，不是 enterprise identity 或 tenant platform。

## 明确非目标

- 生产 runtime 中的 OCR、扫描件识别、raw PDF/Word/Excel/image parsing。
- 完整 RAG/vector search service 或在线 retrieval backend。
- Model training、fine-tuning，或从 LLM output 自动激活 production rules。
- Enterprise SSO、tenant-aware authorization、TLS termination、managed secret storage、hosted credential provisioning 或 model/provider monitoring。

## 给评审者的说明

- Package verification 证明 package structure、hashes、required artifacts、parseability 和 traceability；不等同于每个 target field 都通过 strict semantic validation。
- Retrieval evaluator 是确定性轻量证据，用于说明 chunk organization，不是 production RAG system。
- Gold labels 和 badcases 是 coursework-scale evaluation assets，不是 enterprise benchmark。
- 当前无独立 production shadow/blind gold corpus，因此不能宣称生产盲测 recall 0.85。

## 五项深化补充

| Requirement | Evidence |
| --- | --- |
| Non-procurement strict quality | Phase C/D gap analysis、strengthened catalogs、non-procurement evaluator；Phase D strict pass 39/50 |
| Real UIR depth | 60-document manifest、inventory、mapping/badcase/retrieval gold；60/60 全链路通过 |
| Content organization quality | strategy、summary-faithfulness 和 tag-quality reports |
| Human-review growth | 独立 review-to-active-pack evaluator，带 snapshot/reject/badcase guards |
| Downstream consumption | CSV、RAG JSONL、45-package contract report、workbench readiness panel |

## 非采购 Recall 验收补充

| Requirement | 当前证据 | 状态 |
| --- | --- | --- |
| 在不走捷径的前提下提升非采购 mapping recall | 当前 average recall `0.8063730159`，badcase violations 0。 | 已提升 |
| 达到 Phase D strict gate | strict pass 39/50，required missing 2，package verification 50/50。 | 已达成 |
| 达到 average recall ≥ 0.78 | 当前 `0.8063730159`。 | 已达成 |
| 降低 review-required | 当前 16，目标 ≤18。 | 已达成 |
| 保持 badcase filters 生效 | `发布日期 -> effective_date`、`retrieved_at -> effective_date` 等 unsafe mappings 未被自动接受。 | 已保护 |

详见 [`reports/phase_d_non_procurement_mapping_eval_report.md`](../../reports/phase_d_non_procurement_mapping_eval_report.md)、
[`reports/phase_d_semantic_mapping_quality_report.md`](../../reports/phase_d_semantic_mapping_quality_report.md) 和
[`reports/phase_d_strict_validation_failure_analysis.md`](../../reports/phase_d_strict_validation_failure_analysis.md)。

## External UIR API/UI Requirement Mapping

- External UIR JSON can be converted through `POST /api/v1/external-uir/convert`.
- Adapter reports preserve deterministic trace evidence and external paths.
- Schema routing is returned as `route_report` for manual review before import and task creation.
- `POST /api/v1/external-uir/import` imports the converted standard UIR through `DocumentService` without creating or executing a task.
- `POST /api/v1/external-uir/create-task` creates a task from an imported document and explicit schema/template choices without executing it.
- DeepSeek is disabled by default and limited to adapter suggestions; auto accepted LLM mappings remain zero.
- The frontend workbench includes an External UIR Adapter panel for Convert -> Preview -> Import -> Create Task.
