# SchemaPack Agent 当前实施状态

> 最后同步：2026-07-09。本文档是项目能力、验证基线、评测证据和边界的统一状态入口。
> 当前分支：`codex/strengthen-topic5-final-gate`；当前状态：项目主链路已可复现，strengthen-stage evidence pack 已生成，最终综合门禁为 `conditional_pass`。
> 历史需求、规格和实施计划保留当时语境；发生冲突时，以本文档、
> [`README.md`](README.md) 和 [`../openapi.json`](../openapi.json) 为准。

## 验证基线

上一轮完整仓库级验证：

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
Push-Location frontend
npm.cmd test
Pop-Location
```

已知结果：

- Backend pytest：当前 basic-stage 验证 733 passed。
- Backend Ruff：当前 basic-stage 验证 clean。
- Frontend production build：当前 basic-stage 验证 successful。
- Frontend tests：当前 basic-stage 验证 24 passed，8 test files passed。
- API：当前 basic-stage 验证 63 OpenAPI paths exported to [`../openapi.json`](../openapi.json)。
- Regression gates：上一完整基线 8/8 passed。
- Basic-stage 一键复现：`.\scripts\run_basic_stage_verification.ps1` 已生成 `docs/交接/evidence/basic_stage/`。
- Strengthen-stage 一键复现：`.\scripts\run_strengthen_stage_verification.ps1` 已生成 `docs/交接/evidence/strengthen_stage/`。

质量专项当前结论：仓库级验证与 evidence pack 可复现；strengthen-stage mapping quality gate 已通过，final gate 为 `conditional_pass`。主要 partial 项为 review-required rate 超出 0.08 目标、Codex review 未声明 live subagent、content quality 未全面达标。

## 已实施能力

| 阶段/能力 | 状态 | 当前实现 |
| --- | --- | --- |
| Core pipeline | 已完成 | UIR/External UIR -> Schema/Template Snapshot -> Candidate Extraction -> Mapping -> Transform -> Canonical -> Render -> Content Organization -> Validate -> Manifest -> ZIP -> Verify |
| Catalog governance | 已完成 | schema/template versions、effective template resolution、knowledge-pack draft/active/archive、历史 task snapshot 保护 |
| External UIR | 已完成 | block-list 与 section-tree adapter、adapter trace、router v2、convert/import/create-task API、前端面板 |
| Schema/Template Draft Lab | 已完成 | 字段发现、draft 生成、风险检查、校验与显式导出；draft 不自动激活 |
| Review Workbench | 已完成 | review grouping、impact preview、batch safety、负知识、knowledge diff/impact/rollback |
| Evaluation Center | 已完成 | dataset/run/metric/scorecard API、报告读取、regression gates |
| Package 1.1 / downstream | 已完成 | manifest、hash、strict package verifier、RAG/training/CSV consumer contracts、CLI、Python SDK、adapter scaffold |
| Optional raw upstream | 离线可选 | Docling/Unstructured entry scripts 惰性依赖，输出 External UIR；不进入 backend runtime 默认依赖 |
| SchemaPack-Lineage | 已完成（MVP） | 字段/block/chunk/artifact lineage、五个查询 API、前端 panel、evaluator 与 hard gates |
| DeepSeek / LLM | 安全受控 | provider smoke 与 report-only suggestions；不自动接受 mapping，不激活 schema/template，不创建或执行 task |

核心生产链路保持：

```text
UIR -> Schema/Template Snapshot -> Candidate Extraction -> Mapping
-> Transform -> Canonical -> Render -> Content Organization
-> Validate -> Manifest -> ZIP -> Verify
```

## 评测证据

### Real-world corpus

- Inventory：60 UIR、60 mapping gold、120 retrieval queries、66 badcases。
- 文档类型：general 15、meeting 15、policy 20、procurement 10。
- `reports/real_world_eval_report.json`：60/60 import、60/60 execution、60/60 package verify。
- `reports/real_world_mapping_eval_report.json`：overall mapping recall `0.6831896552`，package pass 60/60，validation pass 40/60，badcase violations 0。

### Non-procurement semantic mapping sprint

- Phase C sprint4：50 samples，average recall `0.7165476190`，strict pass 31/50，required missing 4，review-required 22，package 50/50，badcase violations 0。
- Phase D：50 samples，average recall `0.7426031746`，strict pass 39/50，required missing 2，review-required 21，package 50/50，badcase violations 0。
- 当前 basic-stage 评测记录：50 samples，auto mapping recall `0.777`，assisted mapping recall `0.807`，strict pass 48/50，required missing 0，review-required 24，review-required rate `0.057`，package 50/50，badcase violations 0。
- 当前非采购语义评测 by doc type：
  - general_doc：15 docs，recall `0.7714285714`，strict pass 14/15；
  - meeting_doc：15 docs，recall `0.8072222222`，strict pass 15/15；
  - policy_doc：20 docs，recall `0.8319444444`，strict pass 18/20。
- 当前最大瓶颈转为 dev/test/blind assisted recall 不足和 source-name exact recall：required gaps 已清零，但 dev assisted recall `0.798`、test assisted recall `0.794`、blind assisted recall `0.826`，仍不能宣称 0.85 gate 通过。
- 当前不能宣称 assisted recall 达到 0.85，也不能宣称生产盲测 0.85。

### Strengthen-stage final gate

- 50-sample non-procurement：auto mapping recall `0.812`，assisted mapping recall `0.861`。
- Split assisted recall：dev `0.868`、test `0.868`、blind `0.884`。
- Required missing 0，badcase violations 0，package verification 50/50，overfit scan pass。
- Review-required 48，review-required rate `0.109`，高于 0.08 目标，需诚实说明。
- DeepSeek live report-only：15 requests，unsafe_suggestion_count 0，secret leaks 0，LLM auto accepted 0。
- Codex review dry-run：reviewed_items 48，applied_count 0，production_write_count 0，`can_claim_live_subagent_review = false`。
- Final gate：`conditional_pass`，证据位于 `docs/交接/evidence/strengthen_stage/final/strengthen_stage_final_gate_result.md`。

### UIR Quality Gate、DeepSeek 与 Review Judge

- UIR Quality Gate：60 total，12 pass，48 review，0 reject，0 unsupported，allow-auto-accept 12。
- DeepSeek provider smoke：passed；basic-stage suggestion eval report-only，suggestion_count 20，LLM auto accepted 0，secret leaks 0。
- Codex review subagent dry-run：reviewed_items 23，unsafe approve 0，applied_count 0。
- DeepSeek ablation：report-only not applied；measurable contribution 0.0；LLM auto accepted 0。
- Review judge dry-run：pending 979，suggest reject 26，suggest approve 0，unsafe skipped 953，errors 0。
- Safe apply：applied approve 0，applied reject 0，kept pending 979。
- Secret redaction audit：passed；exact secret file hits 0；secret leaks 0。

### Lineage 与 downstream

- Lineage parse/field/chunk/artifact coverage 均为 1.0，broken edges 0，secret leaks 0，LLM auto accepted 0。
- Evaluation Center 当前 regression gate reports 为 8/8 passed。
- Downstream consumer contract report：45/45 packages passed。

## 当前暂停点

- 本轮评测使用临时 backend `http://127.0.0.1:18000`；恢复评测前需要重新启动 backend。
- 最新 sprint 证据位于 `docs/交接/evidence/`，执行记录见 `docs/交接/mapping_recall_085_guarded_sprint.md`。
- 本轮新增/修改了 policy/general/meeting semantic mapping 相关抽取和排序逻辑；工作区存在未提交改动，不应回滚无关文件。
- 后续优先处理低风险 source-name 修复与 general/meeting 长尾字段对齐，避免 doc_id 特例和 review-required 膨胀。

## 项目边界

- 当前系统面向已进入 UIR / External UIR JSON 的结构化内容，不承诺生产 OCR。
- Optional raw upstream 是离线入口，不进入 backend runtime 默认依赖。
- Package Verification 只证明结构与包契约有效，不等同于字段语义完全正确。
- DeepSeek/LLM suggestion 只能 report-only 或进入人工 Review，不得自动 accepted、激活 catalog 或写入生产规则。
- 当前没有独立 production shadow/blind gold corpus；不能宣称生产盲测 recall 0.85。
