# Real-world UIR 数据集

## 目的

Real-world UIR dataset 用可追溯的公开文档测试 SchemaPack Agent，而不只依赖 synthetic inputs。它不扩大生产 runtime boundary：产品仍从 UIR input 开始。

## 分布

当前扩展后的数据集包含 30 个 UIR documents，覆盖 `general_doc`、`meeting_doc`、`policy_doc` 和 `procurement_doc`。其中非采购 recall 子集为 20 个 documents：

```text
general_doc: 4
meeting_doc: 6
policy_doc: 10
total: 20
```

其余 10 个为 `procurement_doc` samples。

数据集包含公开官方 HTML pages 与 text-layer PDFs。Scanned documents 与 OCR workflows 仍在工具链之外。

## Source Manifest 与 Cached Sources

Source manifest：

```text
examples/real_world/sources/source_manifest.json
```

Collector 会把有限公开 sources 下载到 ignored local cache，并记录 source URL、source site、retrieval timestamp、source format、SHA-256 和 extraction method。Cache 可随时删除并从 manifest 重建。

Sources 必须是无需登录、付费、CAPTCHA 或 anti-bot bypass 即可访问的公开官方材料。Private records、copied mirrors、news/social posts、paid material 和 personal-information-heavy sources 被排除。

## Deterministic Extraction 与 Validation

从 `F:\p2` 运行：

```powershell
backend\.venv\Scripts\python.exe scripts\collect_real_world_sources.py
backend\.venv\Scripts\python.exe scripts\build_real_world_uir.py
backend\.venv\Scripts\python.exe scripts\validate_real_world_uir.py
```

输出包括：

- `examples/real_world/reports/extraction_report.{json,md}`
- `examples/real_world/reports/validation_report.{json,md}`
- `examples/real_world/uir/` 下的 generated UIR JSON files

Validation 检查 strict `UIRDocument` model、filename/doc_id alignment、document type、HTTP(S) source URL、traceability metadata、SHA-256 shape、block minimums、unique block IDs、non-empty text blocks、parseable tables、mojibake markers、privacy patterns、assisted-candidate evidence 和 low-confidence candidates 的 review-required flags。

## Gold Labels、Badcases 与 Retrieval Queries

Additional evaluation labels 位于 `examples/real_world/gold/`：

- `mapping_gold.jsonl`：source-backed mapping rows，包含 source paths、expected mappings、review-required items 和 embedded badcases。
- `real_world_badcases.jsonl`：deterministic flattened badcase view。
- `retrieval_queries.jsonl`：retrieval queries，并带 relevant source block IDs。

Retrieval evaluator 是 deterministic lightweight evaluator，用于衡量 chunk ranking evidence，而不是 full RAG/vector-search service。

## API-Backed 评估

从 `F:\p2` 启动 backend：

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

另一个 `F:\p2` 终端运行 evaluators：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json
```

Offline report commands：

```powershell
backend\.venv\Scripts\python.exe scripts\eval_content_organization_retrieval.py
backend\.venv\Scripts\python.exe scripts\eval_real_world_knowledge_loop.py
backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py --packages-root reports\real_world_packages --gold examples\real_world\gold\mapping_gold.jsonl --badcases examples\real_world\gold\real_world_badcases.jsonl --out reports\non_procurement_gap_analysis.json --markdown reports\non_procurement_gap_analysis.md
```

如启用 API-key authentication，请在脚本支持时传入 API key。Keys 通过 headers 发送，不应出现在 reports 中。

## 当前 Evaluation Results

当前提交证据记录：

- dataset size：30；
- imports：30/30；
- task executions：30/30；
- package verification：30/30；
- real-world mapping badcase violations：0；
- real-world mapping recall：`0.48847926267281105`；
- 非采购 API-backed evaluator：20/20 package verification，badcase violations 0，average recall `0.4211309523809524`，review-required 149，required missing 12；
- 非采购 Phase 1 未达标：recall 与 review-required target 仍未达到。

Primary reports：

- `reports/real_world_eval_report.{json,md}`
- `reports/real_world_mapping_eval_report.{json,md}`
- `reports/non_procurement_mapping_eval_report.{json,md}`
- `reports/non_procurement_acceptance_report.md`
- `reports/non_procurement_gap_analysis.{json,md}`
- `reports/procurement_doc_eval_report.{json,md}`
- `reports/content_organization_retrieval_eval.{json,md}`
- `reports/knowledge_loop_eval_report.{json,md}`
- `reports/real_world_knowledge_loop_report.{json,md}`

## 限制

- HTML layout heuristics 不能完美隔离所有政府网站内容模板。
- PDF heading detection 较保守，并依赖可用 font metadata。
- Complex merged-cell tables 会被 flatten 为 field/value rows。
- Collector 有意保持 small-scale 与 sequential。
- Deterministic generation 不需要 LLM。
- Procurement schema aliases 需要持续 real-sample review。
- Gold labels 是 coursework-scale evaluation labels，不是 enterprise benchmark。
- OCR、scanned PDFs、image parsing、full RAG/vector search 和 model training 仍在 implemented dataset/evaluator boundary 之外。
