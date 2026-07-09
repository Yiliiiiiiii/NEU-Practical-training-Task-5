# SchemaPack Agent 课题 5 当前验收报告

> 同步时间：2026-07-07
> 基线 commit：`7fd38c77 feat: add phase D/E/F review safety reports`
> 本报告只陈述当前可复现证据；未运行、缺失或部分达标的检查不会被表述为完成。

## 1. 项目定位

SchemaPack Agent 面向已经进入 UIR / External UIR JSON 的文档内容，提供受 Schema 和 Mapping
约束的确定性转换、校验、成果包生成、人审闭环、安全建议与可追溯证据。验收对象是可复现的工程证据，而不是对缺失检查的推测。

## 2. 核心链路

```text
UIR / External UIR JSON
-> Adapter / Schema Router
-> Schema/Template Snapshot
-> Candidate Extraction
-> Mapping + Review / Knowledge
-> Transform + Canonical
-> Render + Content Organization
-> Validate
-> Manifest + ZIP
-> Verify + Consumer Contract
```

## 3. 仓库级验证

| 检查 | 当前结果 | 复现命令 |
| --- | --- | --- |
| backend pytest | 662 passed | `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi` |
| backend ruff | clean | 同上 |
| frontend build | successful | 同上 |
| OpenAPI export/check | 63 paths | 同上 |
| frontend tests | 24 passed / 8 files | `Push-Location frontend; npm.cmd test; Pop-Location` |
| regression gates | 8/8 passed | `scripts\check_regression_gates.py` |

## 4. 当前实现能力总览

| 能力 | 状态 | 证据 |
| --- | --- | --- |
| 标准 UIR 转换与成果包 | 已实现 | `reports/real_world_eval_report.json`、`reports/real_world_mapping_eval_report.json` |
| External UIR adapter/router/API/UI | 已实现 | `reports/external_uir_adapter_eval_report.json`、`docs/external_uir_integration.md` |
| Review/Knowledge 治理 | 已实现 | `reports/review_knowledge_growth_report.json`、Review/Knowledge APIs |
| Evaluation Center / regression gates | 已实现 | `reports/evaluation_center/` |
| Package 1.1 / downstream contracts | 已实现 | `docs/package_spec.md`、`reports/downstream_contract_eval_report.json` |
| SchemaPack-Lineage | MVP 已实现 | `docs/lineage.md`、`reports/lineage_eval_report.json` |
| UIR Quality Gate | 已实现 | `reports/uir_quality_gate_eval_report.json` |
| DeepSeek / LLM suggestion | 安全受控 | `reports/deepseek_provider_smoke_report.json`、`reports/deepseek_ablation_report.json` |
| Review judge subagent simulation | report-only / guarded | `reports/review_judge_subagent_report.json`、`reports/ai_review_apply_report.json` |

## 5. 真实 UIR 与映射评测

- Inventory：60 UIR、60 mapping gold、120 retrieval queries、66 badcases。
- `reports/real_world_eval_report.json`：
  - dataset_size 60；
  - import pass 60/60；
  - task execution pass 60/60；
  - package verify pass 60/60；
  - high-risk mapping count 0。
- `reports/real_world_mapping_eval_report.json`：
  - overall mapping recall `0.6831896552`；
  - package pass 60/60；
  - validation pass 40/60；
  - badcase violations 0。

## 6. 非采购语义评测专项

| 指标 | Phase C sprint4 | Phase D | 当前记录 |
| --- | ---: | ---: | ---: |
| dataset size | 50 | 50 | 50 |
| assisted recall | `0.7165476190` | `0.7426031746` | `0.8096514745` |
| auto recall | - | - | `0.7774798928` |
| strict pass | 31/50 | 39/50 | 48/50 |
| required missing | 4 | 2 | 0 |
| review-required | 22 | 21 | 18 |
| review-required rate | - | - | `0.0435835351` |
| package verify | 50/50 | 50/50 | 50/50 |
| badcase violations | 0 | 0 | 0 |

当前记录达成：strict pass ≥ 43/50、required missing = 0、badcase violations = 0、package verification = 50/50、overfit scan pass。

当前记录未达成：assisted recall ≥ 0.85。当前 quality gate 失败原因是 dev assisted recall `0.807 < 0.850`、test assisted recall `0.794 < 0.850`；blind assisted recall 已到 `0.855`。

## 7. UIR Quality Gate、DeepSeek 与 Review Judge

- UIR Quality Gate：60 total，12 pass，48 review，0 reject，0 unsupported，allow-auto-accept 12。
- DeepSeek provider smoke：passed；suggestion_count 2；warning_count 0；secret_leak_detected false。
- DeepSeek ablation：report-only not applied；measurable contribution 0.0；LLM auto accepted 0。
- Review judge dry-run：pending 979，suggest reject 26，suggest approve 0，unsafe skipped 953，errors 0。
- Safe apply：applied approve 0，applied reject 0，kept pending 979。
- Secret redaction audit：passed；exact secret file hits 0；secret leaks 0。

## 8. 下游消费与 Lineage

- Downstream contract report：45/45 packages passed，0 failures。
- Lineage parse/field/chunk/artifact coverage 均为 1.0。
- Lineage broken edges 0、secret leaks 0、LLM auto accepted 0。
- Lineage graph/summary 当前作为 task reports，不进入 Package 1.1 ZIP。

## 9. 项目边界与未实现事项

- 生产 input：UIR 或 External UIR JSON。
- 不提供生产级 raw PDF/Word/Excel/image upload API。
- 不实现 OCR 或扫描件识别。
- 不包含完整 RAG/vector database。
- 不包含模型训练或 fine-tuning。
- DeepSeek/LLM suggestion 不自动接受 mapping，不激活 schema/template，不创建或执行 task。
- 未实现 Webhook、SSO、tenant-aware authorization、TLS termination、managed secret storage、hosted credential provisioning、企业级 model/provider monitoring。

## 10. 0.85 与生产盲测说明

当前不能宣称生产 shadow/blind recall 达到 0.85：

- `reports/blind_set_eval_report.json`：`status = not_run`，`can_claim_0_85 = false`。
- `reports/production_shadow_eval_report.json`：`status = not_run`。
- 原因：当前 workspace 没有独立 production shadow/blind UIR gold corpus。
- 当前 50-sample 非采购语义评测 assisted recall 为 `0.8096514745`，尚未达到 0.85；required missing 已清零，badcase violations 仍为 0。

## 11. 当前结论

项目主链路、External UIR、治理工作台、Lineage、Package/downstream 和安全 suggestion 路径均有可复现工程证据。当前最大剩余缺口是非采购语义质量继续提升，尤其是 dev/test split 的 source-name exact recall 与 general/meeting 长尾字段；生产盲测 0.85 需要先补齐独立 blind/shadow gold corpus。
