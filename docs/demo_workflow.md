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
