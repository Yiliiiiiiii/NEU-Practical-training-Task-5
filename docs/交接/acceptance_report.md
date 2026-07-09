# SchemaPack Agent 课题 5 当前验收报告

> 同步时间：2026-07-09
> 基线 commit：`7fd38c77 feat: add phase D/E/F review safety reports`
> 本报告只陈述当前可复现证据；未运行、缺失或部分达标的检查不会被表述为完成。

## 1. 项目定位

SchemaPack Agent 面向已经进入 UIR / External UIR JSON 的文档内容，提供受 Schema 和 Mapping
约束的确定性转换、校验、成果包生成、人审闭环、安全建议与可追溯证据。验收对象是可复现的工程证据，而不是对缺失检查的推测。

## 2. 核心链路

```text
UIR + Target Schema + Metadata Template + Mapping Rules + Content Organization Config
-> Config Validation
-> Generic Candidate Extraction
-> Schema-aware Mapping
-> Transform + Canonical
-> Render + Content Organization
-> Validate
-> Manifest + ZIP
-> Verify + Consumer Contract
```

## 课题 5 主线纠偏结论

当前验收以 Topic 5 标准输入模型为主：UIR + Target Schema + Metadata Template + Mapping Rules + Content Organization Config。原有 catalog schema/template 是复用配置，不是唯一入口。新增 no-code announcement_doc SchemaPack 证明系统可以在不修改核心映射代码的情况下接入新的目标结构。

SchemaPack 只是示例配置与评测基准，不是系统能力边界。

## 3. 仓库级验证

| 检查 | 当前结果 | 复现命令 |
| --- | --- | --- |
| backend pytest | 733 passed | `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi` |
| backend ruff | clean | 同上 |
| frontend build | successful | 同上 |
| OpenAPI export/check | 63 paths | 同上 |
| frontend tests | 24 passed / 8 files | `Push-Location frontend; npm.cmd test; Pop-Location` |
| regression gates | 8/8 passed | `scripts\check_regression_gates.py` |
| basic-stage evidence pack | generated, mapping gate partial | `.\scripts\run_basic_stage_verification.ps1` |
| strengthen-stage evidence pack | generated, final gate conditional_pass | `.\scripts\run_strengthen_stage_verification.ps1` |

强化阶段最新综合结论见 `docs/交接/evidence/strengthen_stage/final/strengthen_stage_final_gate_result.md`。该结论为 `conditional_pass`：mapping/package/overfit/operation/schema 已通过；LLM、Codex review、content quality 和 doc consistency 按证据诚实标记为 partial。

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
| assisted recall | `0.7165476190` | `0.7426031746` | `0.807` |
| auto recall | - | - | `0.777` |
| strict pass | 31/50 | 39/50 | 48/50 |
| required missing | 4 | 2 | 0 |
| review-required | 22 | 21 | 24 |
| review-required rate | - | - | `0.057` |
| package verify | 50/50 | 50/50 | 50/50 |
| badcase violations | 0 | 0 | 0 |

Basic-stage split assisted recall: dev `0.798`、test `0.794`、blind `0.826`。Quality gate 未通过，失败原因已记录于 `docs/交接/evidence/basic_stage/mapping/mapping_quality_gate_result.md`；不得宣称 0.85 已达成。

当前记录达成：strict pass ≥ 43/50、required missing = 0、badcase violations = 0、package verification = 50/50、overfit scan pass。

当前记录未达成：assisted recall ≥ 0.85。当前 quality gate 失败原因是 dev assisted recall `0.807 < 0.850`、test assisted recall `0.794 < 0.850`；blind assisted recall 已到 `0.855`。

强化阶段最新记录：

| 指标 | strengthen-stage |
| --- | ---: |
| dataset size | 50 |
| auto mapping recall | `0.812` |
| assisted mapping recall | `0.861` |
| dev assisted recall | `0.868` |
| test assisted recall | `0.868` |
| blind assisted recall | `0.884` |
| required missing | 0 |
| badcase violations | 0 |
| package verification | 50/50 |
| review-required | 48 |
| review-required rate | `0.109` |

Strengthen-stage mapping quality gate 已通过；但 review-required rate 高于 `0.08` 目标，因此最终口径保留为 `conditional_pass`，不得表述为“生产级盲测达标”。

## 7. UIR Quality Gate、DeepSeek 与 Review Judge

- UIR Quality Gate：60 total，12 pass，48 review，0 reject，0 unsupported，allow-auto-accept 12。
- DeepSeek provider smoke：passed；suggestion_count 2；warning_count 0；secret_leak_detected false。
- DeepSeek ablation：report-only not applied；measurable contribution 0.0；LLM auto accepted 0。
- Review judge dry-run：pending 979，suggest reject 26，suggest approve 0，unsafe skipped 953，errors 0。
- Safe apply：applied approve 0，applied reject 0，kept pending 979。
- Secret redaction audit：passed；exact secret file hits 0；secret leaks 0。

强化阶段 DeepSeek live report-only：15 requests，top1/top3 hit rate `1.0`，unsafe_suggestion_count 0，secret_leak_count 0，LLM auto accepted 0，activate_rule_count 0，write_template_count 0。所有输出只进入报告，不写生产规则。

强化阶段 Codex review：当前为 dry-run report，reviewed_items 48，unsafe_approve_count 0，applied_count 0，production_write_count 0，`can_claim_live_subagent_review = false`。

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
# Current Topic 5 Acceptance Note

The accepted public inline contract is UIR + target_schema + mapping_rules + metadata_template + content_organization. `mapping_template` remains a legacy-compatible alias only.

The project does not claim production-grade blind recall 0.85. The current stronger mapping metric is assisted recall 0.861, while auto recall still needs improvement. LLM and Codex paths remain report-only or dry-run and do not write production rules.

## Topic 5 Phase 2 Mapping Quality

Phase 2 benchmark evidence is now available in
`reports/topic5_mapping_quality_gate_report.json` and
`reports/topic5_mapping_quality_gate_report.md`.

The `global_assignment` mode passes the standard UIR benchmark gate with
test auto precision 0.9310, test auto recall 1.0000, required missing 0,
badcase violations 0, review-required rate 0.0000, and test-vs-blind gap
0.0000.

Allowed claim: benchmark-level auto mapping recall >= 0.85 within the
declared standard UIR benchmark scope. This is still not a production
shadow/blind recall claim.
