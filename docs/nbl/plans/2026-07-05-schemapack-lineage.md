# SchemaPack-Lineage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use nbl.subagent-driven-development (recommended) or nbl.executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为现有 SchemaPack 转换主链路增加字段、块、chunk 与 artifact 级的可信追溯报告、查询 API、前端展示和回归评估。

**Architecture:** LineageGraphService 在 task 的 package/manifest 已生成后，以只读输入构建旁路 DAG；LineageQueryService 在持久化 graph 上做有界上下游遍历。Lineage 默认启用、失败非阻断，并通过 task report API 暴露；MVP 不把 lineage 自身写入 ZIP，以避免 manifest checksum 自引用并保持 Package 1.1 contract 不变。

**Tech Stack:** Python 3.12、FastAPI、Pydantic v2、SQLAlchemy、pytest、React 18、TypeScript、Vitest。

---

## 文件结构

- Create `backend/app/schemas/lineage.py`: lineage node、edge、evidence、graph、query result 的严格模型。
- Create `backend/app/services/lineage_graph_service.py`: 安全清洗、节点/边生成、summary 计算。
- Create `backend/app/services/lineage_query_service.py`: field/chunk/artifact 根节点解析与有界子图遍历。
- Modify `backend/app/services/task_execution_service.py`: 默认 options、graph 构建、非阻断 warning、report path。
- Create `backend/app/api/v1/lineage.py`: 五个只读 lineage endpoints。
- Modify `backend/app/api/v1/router.py`: 注册 lineage router。
- Modify `backend/app/schemas/external_uir.py`、`backend/app/api/v1/external_uir.py`: create-task 持久化 adapter report。
- Create backend lineage tests: schema、graph、query、task integration、API、evaluator。
- Create `frontend/src/components/LineagePanel.tsx`, `LineageGraphView.tsx`, `LineageNodeDetails.tsx`: 分层 lineage UI。
- Modify `frontend/src/api.ts`, `types.ts`, `App.tsx`, `styles.css`: API、状态、报告区域集成。
- Create `scripts/eval_lineage_graph.py`: 本地/API graph 评估、JSON/Markdown 输出、可选 metrics merge。
- Modify `backend/app/services/metric_registry_service.py`、`evaluation_center_service.py`: lineage gates/cards。
- Update docs and generated OpenAPI/reports.

### Task 1: Lineage schema

**Dependencies:** None  
**Parallelizable:** No（后续服务依赖模型）

**Files:**
- Create: `backend/app/schemas/lineage.py`
- Create: `backend/tests/test_lineage_schema.py`

- [ ] **Step 1: 写失败测试**

覆盖所有 node/edge/status literal，并验证缺失 source/target 的 edge 被拒绝。

- [ ] **Step 2: 验证 RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_lineage_schema.py -q`  
Expected: FAIL，原因是 `app.schemas.lineage` 尚不存在。

- [ ] **Step 3: 实现最小模型**

使用 `StrictBaseModel` 和执行文档定义的 literal，所有集合字段使用 `default_factory`。

- [ ] **Step 4: 验证 GREEN**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_lineage_schema.py -q`  
Expected: PASS。

### Task 2: Graph builder

**Dependencies:** Task 1  
**Parallelizable:** No（依赖 schema）

**Files:**
- Create: `backend/app/services/lineage_graph_service.py`
- Create: `backend/tests/test_lineage_graph_service.py`

- [ ] **Step 1: 写失败测试**

构造最小 UIR、candidate、mapping、canonical、chunk、manifest、adapter、review 与 knowledge 输入，断言：

- UIR block/candidate/mapping/schema/canonical/artifact/manifest 链路完整；
- chunk 连到 source blocks 与 `chunks.jsonl`；
- External UIR 生成 `external_field -> adapter_trace -> uir_block`；
- review-required、badcase-blocked 与 knowledge 状态可见；
- metadata 中 secret key 和 `sk-`/bearer 字符串不会泄漏；
- 每条 edge 的两端都存在。

- [ ] **Step 2: 验证 RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_lineage_graph_service.py -q`  
Expected: FAIL，原因是 service 尚不存在。

- [ ] **Step 3: 实现最小 builder**

公开接口：

```python
LineageGraphService().build(
    *,
    task_id,
    doc_id,
    uir,
    candidates,
    mapping_report,
    schema,
    template,
    canonical,
    chunks,
    manifest,
    adapter_report=None,
    review_decisions=(),
    knowledge_records=(),
    applied_knowledge_pack_ids=(),
) -> LineageGraph
```

builder 使用确定性 node id、去重 add-node/add-edge、递归安全清洗和无断边 summary。

- [ ] **Step 4: 验证 GREEN**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_lineage_graph_service.py -q`  
Expected: PASS。

### Task 3: Query service

**Dependencies:** Task 1, Task 2  
**Parallelizable:** No（依赖 graph 语义）

**Files:**
- Create: `backend/app/services/lineage_query_service.py`
- Create: `backend/tests/test_lineage_query_service.py`

- [ ] **Step 1: 写失败测试**

覆盖 field upstream、chunk upstream/both、artifact upstream/downstream、未知 root 的一致行为与 `max_depth`。

- [ ] **Step 2: 验证 RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_lineage_query_service.py -q`  
Expected: FAIL，原因是 query service 尚不存在。

- [ ] **Step 3: 实现有界遍历**

索引 incoming/outgoing edges，BFS 遍历并只返回被选 edge 引用的 evidence；未知 field/chunk/artifact 抛 `LookupError`。

- [ ] **Step 4: 验证 GREEN**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_lineage_query_service.py -q`  
Expected: PASS。

### Task 4: Task execution 与 External UIR evidence

**Dependencies:** Task 2  
**Parallelizable:** No（修改主执行协调层）

**Files:**
- Modify: `backend/app/services/task_execution_service.py`
- Modify: `backend/app/schemas/external_uir.py`
- Modify: `backend/app/api/v1/external_uir.py`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/components/ExternalUirPanel.tsx`
- Create: `backend/tests/test_lineage_task_integration.py`

- [ ] **Step 1: 写失败测试**

覆盖默认启用、report paths、strict/non-strict failure、adapter report task option 持久化和既有 task status 不变。

- [ ] **Step 2: 验证 RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_lineage_task_integration.py -q`  
Expected: FAIL，lineage reports 尚未生成。

- [ ] **Step 3: 集成旁路构建**

package 完成后构建 graph，写 `tasks/{task_id}/lineage_graph.json` 与 `lineage_summary.json`；非 strict 异常追加 `lineage_warnings`，strict 异常上抛。

- [ ] **Step 4: 持久化 adapter report**

`ExternalUIRCreateTaskRequest` 接受 optional adapter report，API 放入 `options.external_uir.adapter_report`，前端 create-task 传当前转换结果。

- [ ] **Step 5: 验证 GREEN**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_lineage_task_integration.py backend\tests\test_external_uir_api.py -q`  
Expected: PASS。

### Task 5: Lineage API 与 OpenAPI

**Dependencies:** Task 3, Task 4  
**Parallelizable:** No（依赖持久化 graph）

**Files:**
- Create: `backend/app/api/v1/lineage.py`
- Modify: `backend/app/api/v1/router.py`
- Create: `backend/tests/test_lineage_api.py`
- Generate: `docs/openapi.json`

- [ ] **Step 1: 写失败 API 测试**

覆盖 graph、summary、field、chunk、artifact、未知 task/root 与 secret 不泄漏。

- [ ] **Step 2: 验证 RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_lineage_api.py -q`  
Expected: FAIL 404，route 尚未注册。

- [ ] **Step 3: 实现 endpoints**

复用 task execution dependency 和安全 report 读取；query params 为 `direction` 与 `max_depth`。

- [ ] **Step 4: 验证 GREEN 并导出 OpenAPI**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_lineage_api.py -q
backend\.venv\Scripts\python.exe scripts\export_openapi.py
```

Expected: tests PASS，OpenAPI 包含五个 lineage path。

### Task 6: Frontend Lineage Panel

**Dependencies:** Task 5  
**Parallelizable:** No（依赖 API contract）

**Files:**
- Create: `frontend/src/components/LineagePanel.tsx`
- Create: `frontend/src/components/LineageGraphView.tsx`
- Create: `frontend/src/components/LineageNodeDetails.tsx`
- Create: `frontend/src/__tests__/LineagePanel.test.tsx`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: 写失败组件测试**

覆盖 summary cards、field/chunk/artifact 查询、review_required/blocked 文本、固定语义警告与 API error。

- [ ] **Step 2: 验证 RED**

Run: `Push-Location frontend; npm.cmd test -- LineagePanel.test.tsx; Pop-Location`  
Expected: FAIL，组件尚不存在。

- [ ] **Step 3: 实现分层列表 UI**

Panel 自主管理查询类型、root 与错误状态；GraphView 展示层级路径与显式 status 文本；NodeDetails 展示 evidence/metadata。

- [ ] **Step 4: 集成 App**

Task artifacts 刷新时读取 summary/graph，在 report inspection 区增加“可信链路”面板。

- [ ] **Step 5: 验证 GREEN**

Run:

```powershell
Push-Location frontend
npm.cmd test
npm.cmd run build
Pop-Location
```

Expected: tests PASS，build exit 0。

### Task 7: Evaluator 与 Evaluation Center

**Dependencies:** Task 2, Task 5  
**Parallelizable:** No（依赖最终 graph contract）

**Files:**
- Create: `scripts/eval_lineage_graph.py`
- Create: `backend/tests/test_eval_lineage_graph_script.py`
- Modify: `backend/app/services/metric_registry_service.py`
- Modify: `backend/app/services/evaluation_center_service.py`
- Modify: `backend/tests/test_evaluation_center_service.py`
- Generate: `reports/lineage_eval_report.json`
- Generate: `reports/lineage_eval_report.md`
- Generate: `reports/evaluation_center/current_metrics.json`
- Modify: `reports/evaluation_center/regression_gates.json`

- [ ] **Step 1: 写失败 evaluator 测试**

覆盖 JSON/Markdown、broken edges、orphan nodes、secret-like values、coverage、LLM auto accepted 和 metrics merge。

- [ ] **Step 2: 验证 RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_eval_lineage_graph_script.py -q`  
Expected: FAIL，script 尚不存在。

- [ ] **Step 3: 实现 evaluator**

支持 `--tasks-root` 与 `--base-url`，输出执行文档要求的全部指标；`--evaluation-metrics` 显式把四个 lineage gate 指标合并到 current metrics，并保留 sources。

- [ ] **Step 4: 接入 registry 与 scorecard**

新增 parse、broken edge、secret leak、field coverage metric definitions/gates/cards。

- [ ] **Step 5: 验证 GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_eval_lineage_graph_script.py backend\tests\test_evaluation_center_service.py -q
backend\.venv\Scripts\python.exe scripts\eval_lineage_graph.py --tasks-root storage\tasks --out reports\lineage_eval_report.json --markdown reports\lineage_eval_report.md --evaluation-metrics reports\evaluation_center\current_metrics.json
```

Expected: tests PASS，报告由脚本生成。

### Task 8: 文档与最终验收

**Dependencies:** Task 4, Task 5, Task 6, Task 7  
**Parallelizable:** No（汇总最终行为）

**Files:**
- Create: `docs/lineage.md`
- Modify: `docs/developer_guide.md`
- Modify: `docs/package_spec.md`
- Modify: `docs/api_usage_examples.md`
- Modify: `docs/demo_workflow.md`
- Modify: `docs/交接/final_demo_script.md`
- Modify: `docs/交接/project_status.md`
- Modify: `docs/交接/final_handoff_status.md`
- Modify: `README.md`

- [ ] **Step 1: 更新文档**

说明数据流、API、非阻断模式、安全边界、evaluator、demo，以及 MVP lineage reports 不进入 ZIP 的自引用原因。

- [ ] **Step 2: 运行 backend/OpenAPI 验收**

Run: `backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`  
Expected: exit 0。

- [ ] **Step 3: 运行 frontend 验收**

Run: `Push-Location frontend; npm.cmd test; npm.cmd run build; Pop-Location`  
Expected: tests PASS，build exit 0。

- [ ] **Step 4: 运行 regression gates**

Run:

```powershell
backend\.venv\Scripts\python.exe scripts\check_regression_gates.py `
  --metrics reports\evaluation_center\current_metrics.json `
  --gates reports\evaluation_center\regression_gates.json `
  --out reports\evaluation_center\regression_gate_report.json
```

Expected: exit 0，badcase、LLM、package 与 lineage hard gates 全部通过。

- [ ] **Step 5: 检查工作区差异**

只审阅本计划涉及文件，不覆盖或回滚用户已有未提交改动。当前工作区已有大量用户变更，因此本计划不自动 commit。

---

**Execution Mode:** serial（当前主代理执行；用户未授权子代理）
