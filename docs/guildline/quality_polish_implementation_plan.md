# SchemaPack 三项质量打磨实施计划

**Goal:** 在不改变生产边界和安全门的前提下，提升 strict validation、把 External UIR fixtures 扩充到至少 12 个，并把 Evaluation Center 打磨为可验收的四区块视图。

**Architecture:** 保留现有 UIR → Mapping → Package 主链路。Strict validation 仅增强候选抽取和模板规则；Adapter 通过 fixture contract 驱动转换、路由、trace 与 badcase 评测；Evaluation Center 在现有 API 上扩展 scorecard 模型并由同一份 metrics/gates 生成静态报告和前端视图。

**Tech Stack:** FastAPI、Pydantic、pytest、Python evaluator scripts、React、TypeScript、Vitest、Vite。

---

### Task 1: 固化基线与 strict failure 分析

**Files:**
- Create: `scripts/analyze_strict_validation_failures.py`
- Create: `backend/tests/test_analyze_strict_validation_failures_script.py`
- Create: `reports/quality_polish_baseline.json`
- Create: `reports/quality_polish_baseline.md`

- [ ] 先写脚本测试，要求从 package reports 汇总 doc_type、required missing、review-required 和 failure categories。
- [ ] 运行测试并确认因脚本缺失失败。
- [ ] 实现纯读取分析器，输出 JSON 与 Markdown，不修改 package。
- [ ] 运行测试与分析命令，确认报告可复现。

### Task 2: 提升 meeting/policy strict validation

**Files:**
- Modify: `backend/app/services/candidate_service.py`
- Modify: `examples/production_like/mapping_templates/meeting_doc_base_v1.json`
- Modify: `examples/production_like/mapping_templates/policy_doc_base_v1.json`
- Create: `backend/tests/test_candidate_service_strict_validation.py`
- Create: `backend/tests/test_strict_validation_templates.py`

- [ ] 先为真实 meeting/policy 句式写失败测试，覆盖会议日期/编号/主持人、政策发布机关/日期/文号/实施日期。
- [ ] 确认测试只因缺失候选或规则失败。
- [ ] 最小增强候选抽取和模板 regex/alias；禁止把主持人映射 attendees、成文日期映射 publish_date、retrieved_at 映射 effective_date。
- [ ] 运行定向测试、Ruff 和 API evaluator，记录前后 strict 指标。

### Task 3: 扩充 Adapter fixture contract

**Files:**
- Add fixtures under: `examples/external_uir/dialect_a_block_list/`
- Add fixtures under: `examples/external_uir/dialect_b_section_tree/`
- Create: `examples/external_uir/expected/adapter_expected.jsonl`
- Create: `examples/external_uir/expected/router_expected.jsonl`
- Create: `examples/external_uir/expected/trace_expected.jsonl`
- Create: `examples/external_uir/expected/badcases.jsonl`
- Modify: `scripts/eval_external_uir_adapter.py`
- Modify: `scripts/eval_external_uir_api.py`

- [ ] 先写 fixture、trace、router 和 badcase 测试，使当前 4-fixture evaluator 失败。
- [ ] 新增正常、表格、嵌套、缺字段、噪声和 badcase fixtures，使总数不少于 12。
- [ ] 让 evaluator 从 JSONL contract 发现 fixtures，并输出 selection accuracy、validation、trace coverage、router accuracy、review、badcase、LLM auto accept 和 secret leak 指标。
- [ ] 验证 scaffold 默认 `auto_register=false`，且包含 fixture/badcase/eval 提示。

### Task 4: Evaluation Center scorecard 与前端

**Files:**
- Modify: `backend/app/schemas/evaluation_center.py`
- Modify: `backend/app/services/evaluation_center_service.py`
- Create: `scripts/build_evaluation_center_scorecard.py`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/components/EvaluationCenterPanel.tsx`
- Modify: `frontend/src/styles.css`
- Create: `frontend/src/__tests__/EvaluationCenter.test.tsx`

- [ ] 先写后端和前端失败测试，覆盖 cards、warnings、三态标签、安全指标强制失败与 API error 降级。
- [ ] 扩展 scorecard 为 summary/cards/warnings，同时保留现有字段兼容调用方。
- [ ] 实现 Dataset Registry、Evaluation Runs、Metric Scorecard、Regression Gates 四区块和固定语义说明。
- [ ] 生成 `scorecard.json/.md` 与 regression gate Markdown，运行 Vitest 和 production build。

### Task 5: 总验收与当前文档

**Files:**
- Create: `reports/strict_validation_improvement_report.json`
- Create: `reports/strict_validation_improvement_report.md`
- Create: `reports/quality_polish_final_report.json`
- Create: `reports/quality_polish_final_report.md`
- Update only current-status docs listed by the execution document.

- [ ] 运行 `scripts/verify_all.py --check-openapi`。
- [ ] 运行 frontend tests/build、regression gates 和全部 API-backed evaluators。
- [ ] 确认 badcase=0、LLM auto accepted=0、package verification=1.0、adapter trace coverage≥0.95。
- [ ] 生成最终 before/after、known gaps、明确未做事项与复现命令。
