# 课题 5 需求映射

本文档把课题 5 要求映射到当前 SchemaPack Agent 的实现和已提交证据。

| Requirement | 当前实现 | 证据 |
| --- | --- | --- |
| Standardization | UIR import、schema/template snapshots、deterministic mapping、transform、canonical model、structured JSON、Markdown 和 package output。 | `mapping_report.json`、`transform_report.json`、`canonical.json`、`content.json`、`content.md`、[`docs/package_spec.md`](package_spec.md) |
| Intelligent organization | 确定性 chunk strategies、summaries、keywords、content/management/quality tags、受保护 table/list/code chunks、parent-child metadata 和 source links。 | `content_organization_report.json`、`chunks.jsonl`、[`reports/content_organization_retrieval_eval.md`](../reports/content_organization_retrieval_eval.md) |
| Specialized conversion | 5 个 seeded document catalog families，包括面向采购样本的 dedicated `procurement_doc` schema 和 `procurement_doc_base_v1` template。 | [`reports/procurement_doc_eval_report.md`](../reports/procurement_doc_eval_report.md)、[`docs/real_world_uir_dataset.md`](real_world_uir_dataset.md) |
| Evaluation | Production-like evaluator，以及 16-document real-world import、execution、package、mapping、procurement、retrieval 和 knowledge-loop runs。 | [`reports/production_like_eval_report.md`](../reports/production_like_eval_report.md)、[`reports/real_world_eval_report.md`](../reports/real_world_eval_report.md)、`reports/` 下提交的 JSON/Markdown report pairs |
| Continuous improvement | Review records、review-derived knowledge candidates、accepted/rejected candidate states、draft/active/archived knowledge packs 和 effective-template resolution。 | [`reports/knowledge_loop_eval_report.md`](../reports/knowledge_loop_eval_report.md)、[`reports/real_world_knowledge_loop_report.md`](../reports/real_world_knowledge_loop_report.md)、Review 与 Knowledge APIs |
| Safety and traceability | Mapping evidence、confidence tiers、review-required reasons、badcase filters、immutable task snapshots、manifest hashes、package verifier output、可选 API-key auth、audit logs 和 LLM secret redaction。 | [`docs/api_usage_examples.md`](api_usage_examples.md)、[`docs/final_handoff_status.md`](final_handoff_status.md)、`manifest.json`、`verifier_report.json`、[`reports/llm_fallback_eval_report.md`](../reports/llm_fallback_eval_report.md) |

## 当前证据摘要

- Unified verification：`backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi` 记录 203 个 backend tests、Ruff clean、frontend production build success 和 32 个 OpenAPI paths。
- Real-world pipeline：16/16 imports、16/16 executions、16/16 verifier-passing packages。
- Strict validation：`procurement_doc` 5/5 通过；`general_doc` 0/3、`meeting_doc` 0/3、`policy_doc` 0/5 仍需 Review。
- Procurement specialization：`procurement_doc` required coverage 为 1.000，generic schema 为 0.333。
- Retrieval：32-query content retrieval report 记录 `Recall@3 = 1.000`。
- Knowledge loop：两个 knowledge-loop reports 都保持 snapshots，并记录 zero badcase violations。
- LLM safety：fallback suggestions 保持 review-required，`auto_accepted_count` 为 0，secret redaction 通过。

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

## 五项深化补充

| Requirement | Evidence |
| --- | --- |
| Non-procurement strict quality | gap analysis、strengthened catalogs、non-procurement evaluator |
| Real UIR depth | 45-document manifest、inventory、mapping/badcase/retrieval gold |
| Content organization quality | strategy、summary-faithfulness 和 tag-quality reports |
| Human-review growth | 独立 review-to-active-pack evaluator，带 snapshot/reject/badcase guards |
| Downstream consumption | CSV、RAG JSONL、30-package contract report、workbench readiness panel |

## 非采购 Recall 验收补充

| Requirement | 当前证据 | 状态 |
| --- | --- | --- |
| 在不走捷径的前提下提升非采购 mapping recall | 干净数据库上的 API-backed evaluator 把 expanded 35-document average recall 提升到 `0.5677551020408163`，badcase violations 仍为 0。 | 已验收 |
| 达到深化 recall target | Average recall 高于 `0.55` target。 | 已达标 |
| 降低 review-required 与 required-missing counts | Review-required 70（目标 ≤120），required missing 6（目标 ≤6），package verification 35/35。 | 已达标 |
| 保持 badcase filters 生效 | 新增 regression badcases 覆盖 `发布日期 -> effective_date`、`主持人 -> attendees`、`联系人 -> attendees`、`承办单位 -> issuer`、`预算金额 -> award_amount`、`控制价 -> award_amount` 等 unsafe mappings。 | 已保护 |
| 保持诚实 evaluation evidence | 报告区分 package verification、mapping recall、strict pass 与 remaining semantic gaps，不宣称所有字段语义完全正确。 | 达标 |

详见 [`reports/non_procurement_acceptance_report.md`](../reports/non_procurement_acceptance_report.md) 和 [`docs/non_procurement_mapping_improvement_plan.md`](non_procurement_mapping_improvement_plan.md)。
