# SchemaPack Agent Demo 流程

本流程用于演示当前端到端路径。

1. 推荐一键启动：

   ```powershell
   .\scripts\start_dev.ps1
   ```

   也可以手动启动 backend：

   ```powershell
   cd backend
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. 如果手动启动，请另开一个终端启动 frontend：

   ```powershell
   cd frontend
   npm run dev
   ```

3. 打开工作台：

   ```text
   http://127.0.0.1:5173/
   ```

4. 使用 sample UIR，然后依次执行：

   - 导入
   - 创建 Task
   - 执行

   侧边栏包含确定性的 content organization 控制项。默认 `heading_aware` strategy 适合 demo；也可以选择 `parent_child` 生成 parent chunks 和 child chunks，用于下游 retrieval 测试。

5. 检查生成结果：

   - mapping report
   - validation report
   - content organization report
   - enriched chunk preview：包含 strategy、title path、token estimate、source links、quality tags，以及可选 parent-child ids
   - 可折叠 raw JSON reports
   - review queue 与 knowledge pack controls
   - package metadata
   - ZIP download

## API 流程

同一流程也可以不通过 UI 执行：

```text
GET  /api/v1/schemas
POST /api/v1/schemas
POST /api/v1/schemas/{schema_id}/versions/{version}/activate
GET  /api/v1/templates
POST /api/v1/templates
POST /api/v1/templates/{template_id}/versions/{version}/activate
POST /api/v1/documents/import
POST /api/v1/tasks
POST /api/v1/tasks/{task_id}/execute
GET  /api/v1/tasks/{task_id}/reports/mapping
GET  /api/v1/tasks/{task_id}/reports/validation
GET  /api/v1/tasks/{task_id}/reports/content_organization
GET  /api/v1/tasks/{task_id}/reports/chunks
GET  /api/v1/reviews
GET  /api/v1/knowledge/candidates
GET  /api/v1/knowledge/packs
GET  /api/v1/knowledge/metrics
GET  /api/v1/tasks/{task_id}/package
GET  /api/v1/tasks/{task_id}/package/download
```

## 下游 Smoke 测试

生成 ZIP package 后，可以验证下游 consumer 能否读取：

```powershell
.\backend\.venv\Scripts\python.exe scripts\smoke_rag_ingest.py --package reports\packages\phase_b\packages\pkg_eval_policy_001_standard\standard_package.zip --query "閸掕泛瀹?缁狅紕鎮?
```

将 package chunks 导出为简单的 training-corpus JSONL：

```powershell
.\backend\.venv\Scripts\python.exe scripts\export_training_corpus.py --package reports\packages\phase_b\packages\pkg_eval_policy_001_standard\standard_package.zip --out reports\training_corpus.jsonl
```

OpenAPI snapshot 导出到：

```text
docs/openapi.json
```

重新生成：

```powershell
.\backend\.venv\Scripts\python.exe scripts\export_openapi.py
```

## 五项深化证据运行

运行 review-growth evaluator、三个 content-quality evaluators 和 downstream contract verifier。随后在工作台中，**下游就绪度** 面板会基于当前 task package 显示 CSV、source-linked RAG 和 verifier readiness。
## External UIR API/UI Demo

1. Start the backend and frontend workbench.
2. Open the External UIR Adapter panel.
3. Upload or paste `examples/external_uir/dialect_a_block_list/sample_procurement_external.json`.
4. Click `Convert & Preview` and point out the adapter trace and
   `procurement_doc` route recommendation.
5. Click `Import Standard UIR`.
6. Click `Create Task`, then execute through the existing task pipeline.
7. Show that DeepSeek assistance is off by default and, when requested without
   local configuration, returns a warning while preserving deterministic output.

## Maturity Platform Demo

1. Open `Schema Draft Lab`, discover fields from curated UIR samples, generate
   a draft, and show that validation/export does not activate it.
2. Open `Review Workbench`, group pending items, preview impact, and demonstrate
   that unsafe batch actions are blocked.
3. Show Knowledge Pack conflict/diff/impact/rollback while confirming old task
   snapshots remain unchanged.
4. Open `Evaluation Center`, inspect datasets, runs, metrics, scorecard, and the
   8/8 regression gate report.
   Point out the four explicit sections and the fixed
   `package verification != strict semantic validation` warning.
5. Show the quality-polish evidence: non-procurement strict pass `17/35`,
   review-required `59`, required missing `4`; External UIR fixtures `18/18`
   with trace/router accuracy `1.0`.
6. Run the unified CLI or Python SDK workflow, then verify the resulting ZIP
   against a versioned consumer contract.
7. Explain that the optional Docling/Unstructured scripts are offline upstream
   tools and that scanned-document OCR remains unsupported.

## SchemaPack-Lineage Demo

1. Convert and import an External UIR fixture, then create and execute its task.
2. Open Mapping Evidence for a target field.
3. Open “可信链路”, select the same field, and show External Field → Adapter
   Trace → UIR Block → Candidate → Mapping → Schema → Canonical.
4. Switch to Chunk and show `source_block_ids`; switch to Artifact and show
   manifest role/hash plus the consumer contract.
5. Point out the explicit `待 Review` and `已阻断` labels; color is not the only
   status signal.
6. Open Evaluation Center and show the four lineage gates inside the 8/8 gate
   report.
7. State that traceability is not strict semantic correctness and open
   Validation/Review/Badcase evidence separately.
