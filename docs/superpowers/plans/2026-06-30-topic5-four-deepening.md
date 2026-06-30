# SchemaPack Agent 四项深化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 16 份真实 UIR 增加映射、采购领域、内容组织检索和人审知识闭环的可复现评测证据。

**Architecture:** 保留现有主链路和 `eval_real_world_uir.py`，新增共享评测模块与四个专项 CLI。所有专项 CLI 优先调用现有 HTTP API，度量与报告逻辑保持为可单测的纯函数，采购配置通过现有 catalog 文件发现机制接入。

**Tech Stack:** Python 3.13、FastAPI/httpx、Pydantic、SQLAlchemy、pytest、Ruff、JSON/JSONL、Markdown。

---

### Task 1: 锁定 gold 数据契约

**Files:**
- Create: `backend/tests/test_real_world_mapping_eval.py`
- Create: `examples/real_world/gold/mapping_gold.jsonl`
- Create: `examples/real_world/gold/real_world_badcases.jsonl`

- [ ] **Step 1: 写缺失 gold 文件的失败测试**

```python
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "examples" / "real_world" / "gold" / "mapping_gold.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_real_world_mapping_gold_is_valid_jsonl() -> None:
    rows = load_jsonl(GOLD)
    assert len(rows) == 16
    assert len({row["doc_id"] for row in rows}) == 16
    assert set(Counter(row["doc_type"] for row in rows)) == {
        "policy_doc",
        "procurement_doc",
        "meeting_doc",
        "general_doc",
    }
    for row in rows:
        assert row["schema_id"]
        assert row["template_id"]
        assert len(row["expected_mappings"]) >= 3
        assert all(item["target_field"] for item in row["expected_mappings"])
        assert all(
            item.get("source_name") or item.get("source_path")
            for item in row["expected_mappings"]
        )
        assert all(item.get("reason") for item in row["expected_review_required"])
        assert row["known_badcases"]
```

- [ ] **Step 2: 运行测试并确认因文件缺失失败**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_real_world_mapping_eval.py::test_real_world_mapping_gold_is_valid_jsonl -v`

Expected: FAIL with `FileNotFoundError` for `mapping_gold.jsonl`.

- [ ] **Step 3: 从 16 份现有 UIR 人工整理 gold**

每行使用以下严格结构，`source_name`、`source_path` 和目标字段必须来自对应 UIR 与实际
Schema；采购行使用 `procurement_doc/procurement_doc_base_v1`：

```json
{
  "doc_id": "real_procurement_001_broadcast_security_supervision",
  "doc_type": "procurement_doc",
  "schema_id": "procurement_doc",
  "template_id": "procurement_doc_base_v1",
  "expected_mappings": [
    {
      "source_name": "项目名称",
      "source_path": "metadata.项目名称",
      "target_field": "project_name",
      "required": true,
      "match_type": "exact_or_alias",
      "gold_status": "accepted"
    }
  ],
  "expected_review_required": [],
  "known_badcases": [
    {
      "case_id": "rw_procurement_role_001",
      "source_name": "中标供应商",
      "forbidden_target_field": "purchaser",
      "reason": "supplier_must_not_map_to_purchaser"
    }
  ]
}
```

`real_world_badcases.jsonl` 将内嵌 badcase 展平为带 `doc_id`、`badcase_type`、
`forbidden_auto_mapping`、`expected_behavior` 和 `severity` 的独立记录。

- [ ] **Step 4: 运行 gold 契约测试**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_real_world_mapping_eval.py::test_real_world_mapping_gold_is_valid_jsonl -v`

Expected: PASS with 16 unique documents and all four doc types.

- [ ] **Step 5: 提交 gold 契约**

```powershell
git add backend/tests/test_real_world_mapping_eval.py examples/real_world/gold
git commit -m "test: define real-world mapping gold contract"
```

### Task 2: 新增采购 Schema 与 Template

**Files:**
- Create: `backend/tests/test_procurement_catalog.py`
- Create: `examples/production_like/schemas/procurement_doc_v1.json`
- Create: `examples/production_like/mapping_templates/procurement_doc_base_v1.json`
- Modify: `scripts/eval_real_world_uir.py`

- [ ] **Step 1: 写采购 catalog 的失败测试**

```python
from app.services.schema_service import SchemaService
from app.services.template_service import TemplateService


def test_procurement_schema_and_template_load() -> None:
    schema = SchemaService().load_schema("procurement_doc", "1.0.0")
    template = TemplateService().load_template("procurement_doc_base_v1", "1.0.0")
    fields = {field.field_id for field in schema.fields}
    assert schema.schema_id == "procurement_doc"
    assert {field.field_id for field in schema.fields if field.required} == {
        "title",
        "project_name",
        "purchaser",
    }
    assert template.schema_id == schema.schema_id
    assert set(template.aliases) <= fields
    assert {"project_name", "purchaser", "budget_amount", "award_supplier"} <= set(
        template.aliases
    )
```

再增加使用临时 SQLite 的 catalog 测试，调用
`CatalogGovernanceService.list_schema_records()` 和 `list_template_records()`，断言采购
版本被 seed 为 active，并验证已被任务引用的版本不能归档。

- [ ] **Step 2: 运行测试并确认 catalog 缺失**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_procurement_catalog.py -v`

Expected: FAIL with `LookupError: schema procurement_doc version 1.0.0 not found`.

- [ ] **Step 3: 按现有 JSON 结构增加采购配置**

Schema 字段固定为：

```text
title, project_name, procurement_id, procurement_type, purchaser, agency,
budget_amount, award_supplier, award_amount, announcement_date, bid_deadline,
opening_date, contact_person, contact_phone, source_url, source_site, summary,
content
```

只将 `title`、`project_name`、`purchaser` 设为 required。Template aliases 使用指导文档
列出的项目名称、采购编号、采购方式、采购人、代理机构、预算、中标供应商、中标金额、
公告日期、截止日期、开标日期和来源同义词；regex 只加入项目编号、明确金额和明确日期
标签；enum map 只覆盖已有明确采购方式。

- [ ] **Step 4: 将现有真实 UIR 评测切换到采购 catalog**

```python
"procurement_doc": {
    "schema_id": "procurement_doc",
    "template_id": "procurement_doc_base_v1",
},
```

- [ ] **Step 5: 运行采购和现有真实 UIR 工具测试**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_procurement_catalog.py tests/test_real_world_uir_tools.py -v`

Expected: PASS.

- [ ] **Step 6: 提交采购 catalog**

```powershell
git add backend/tests/test_procurement_catalog.py examples/production_like scripts/eval_real_world_uir.py
git commit -m "feat: add procurement document catalog"
```

### Task 3: 增加共享评测工具和映射度量

**Files:**
- Create: `scripts/eval_support.py`
- Modify: `backend/tests/test_real_world_mapping_eval.py`

- [ ] **Step 1: 写映射度量的失败测试**

```python
def test_mapping_metrics_count_accepted_review_missing_and_badcases() -> None:
    support = load_script("eval_support")
    gold = {
        "expected_mappings": [
            {"source_name": "项目名称", "target_field": "project_name", "required": True},
            {"source_name": "采购人", "target_field": "purchaser", "required": True},
        ],
        "expected_review_required": [
            {
                "source_name": "金额",
                "target_field_candidates": ["budget_amount", "award_amount"],
                "reason": "multiple_amounts",
            }
        ],
        "known_badcases": [
            {
                "source_name": "截止时间",
                "forbidden_target_field": "announcement_date",
            }
        ],
    }
    report = {
        "mappings": [
            {
                "source_field": {"source_name": "项目名称"},
                "target_field_id": "project_name",
                "status": "accepted",
            }
        ],
        "review_required_items": [
            {
                "source_field": {"source_name": "金额"},
                "target_field_id": "budget_amount",
            }
        ],
        "unmapped": [{"field_id": "purchaser", "required": True}],
    }
    metrics = support.score_mapping_report(gold, report)
    assert metrics["auto_accepted_correct"] == 1
    assert metrics["review_required_correct"] == 1
    assert metrics["missing_gold_mappings"] == 1
    assert metrics["badcase_violation_count"] == 0
    assert metrics["mapping_recall"] == 2 / 3
```

- [ ] **Step 2: 运行测试并确认模块缺失**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_real_world_mapping_eval.py::test_mapping_metrics_count_accepted_review_missing_and_badcases -v`

Expected: FAIL because `scripts/eval_support.py` does not exist.

- [ ] **Step 3: 实现最小共享接口**

```python
def load_jsonl(path: Path) -> list[dict[str, Any]]: ...
def write_json(path: Path, payload: dict[str, Any]) -> None: ...
def write_markdown(path: Path, lines: list[str]) -> None: ...
def safe_ratio(numerator: int | float, denominator: int | float) -> float: ...
def score_mapping_report(
    gold: dict[str, Any],
    mapping_report: dict[str, Any],
) -> dict[str, Any]: ...
def aggregate_mapping_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]: ...


class EvaluationHttpClient:
    def import_document(self, uir: dict[str, Any]) -> dict[str, Any]: ...
    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def execute_task(self, task_id: str) -> dict[str, Any]: ...
    def report(self, task_id: str, report_name: str) -> dict[str, Any]: ...
    def package(self, task_id: str) -> dict[str, Any]: ...
```

匹配键优先使用 `(source_name, target_field)`，缺少 source name 时回退
`(source_path, target_field)`。badcase 只有在 forbidden mapping 为 accepted 时才计为违规。

- [ ] **Step 4: 运行映射度量测试**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_real_world_mapping_eval.py -v`

Expected: PASS.

- [ ] **Step 5: 提交共享评测工具**

```powershell
git add scripts/eval_support.py backend/tests/test_real_world_mapping_eval.py
git commit -m "feat: add reusable evaluation metrics"
```

### Task 4: 实现真实映射和采购对比 CLI

**Files:**
- Create: `scripts/eval_real_world_mapping.py`
- Create: `scripts/eval_procurement_doc.py`
- Modify: `backend/tests/test_real_world_mapping_eval.py`
- Modify: `backend/tests/test_procurement_catalog.py`

- [ ] **Step 1: 写报告构建失败测试**

```python
def test_mapping_eval_generates_required_json_and_markdown_sections(tmp_path: Path) -> None:
    evaluator = load_script("eval_real_world_mapping")
    report = evaluator.build_report(
        [
            {
                "doc_id": "doc_1",
                "doc_type": "policy_doc",
                "metrics": {
                    "gold_mapping_count": 3,
                    "auto_accepted_correct": 2,
                    "auto_accepted_wrong": 0,
                    "review_required_correct": 1,
                    "missing_gold_mappings": 0,
                    "badcase_violation_count": 0,
                },
                "package_passed": True,
            }
        ]
    )
    markdown = evaluator.render_markdown(report)
    assert report["summary"]["document_count"] == 1
    assert report["summary"]["package_pass_rate"] == 1.0
    assert "## Per Document Type" in markdown
    assert "## Badcase Violations" in markdown
    assert "## Package Verification Summary" in markdown
```

采购测试使用两个固定结果，断言 delta 为 `procurement_doc - general_doc`，且输出
required coverage、gold recall、missing required、badcase 和 package 指标。

- [ ] **Step 2: 运行测试并确认两个 CLI 缺失**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_real_world_mapping_eval.py tests/test_procurement_catalog.py -v`

Expected: FAIL while loading `eval_real_world_mapping` and `eval_procurement_doc`.

- [ ] **Step 3: 实现真实映射 CLI**

CLI 参数：

```text
--base-url, --api-key, --gold, --uir-dir, --out-json, --out-md, --timeout
```

每个文档调用 import、create task、execute、mapping report、validation report、verifier
report 和 package metadata。`build_report()` 汇总总体、per doc type、per document、
per field、missing/ambiguous、badcase、review evidence 和 package 结果。连接失败直接
退出；单文档执行失败记录错误并继续。

- [ ] **Step 4: 实现采购对比 CLI**

复用同一执行函数，对五个采购 gold 行分别覆盖 catalog 配置：

```python
GENERAL = ("general_doc", "general_doc_base_v1")
PROCUREMENT = ("procurement_doc", "procurement_doc_base_v1")
```

报告包含两侧指标和 delta，不把 review_required 当作自动错误。

- [ ] **Step 5: 运行专项测试**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_real_world_mapping_eval.py tests/test_procurement_catalog.py -v`

Expected: PASS.

- [ ] **Step 6: 提交两个 CLI**

```powershell
git add scripts/eval_real_world_mapping.py scripts/eval_procurement_doc.py backend/tests
git commit -m "feat: evaluate real-world mapping and procurement coverage"
```

### Task 5: 增加检索 gold 与纯函数指标

**Files:**
- Create: `examples/real_world/gold/retrieval_queries.jsonl`
- Create: `backend/tests/test_content_organization_retrieval_eval.py`
- Create: `scripts/eval_content_organization_retrieval.py`

- [ ] **Step 1: 写查询 gold 和检索指标失败测试**

```python
def test_real_world_retrieval_queries_are_valid_jsonl() -> None:
    rows = load_jsonl(QUERIES)
    assert len(rows) >= 32
    assert len({row["doc_id"] for row in rows}) == 16
    assert all(row["query"].strip() for row in rows)
    assert all(
        row["relevant_source_block_ids"]
        or row["relevant_title_path_contains"]
        or row["relevant_keywords"]
        for row in rows
    )
    by_type = Counter(row["doc_type"] for row in rows)
    assert all(by_type[name] >= 6 for name in (
        "policy_doc",
        "procurement_doc",
        "meeting_doc",
        "general_doc",
    ))


def test_retrieval_metrics_compute_known_ranking() -> None:
    evaluator = load_script("eval_content_organization_retrieval")
    relevant = [False, True, False, True, False]
    metrics = evaluator.ranking_metrics(relevant)
    assert metrics["Recall@1"] == 0.0
    assert metrics["Recall@3"] == 1.0
    assert metrics["Recall@5"] == 1.0
    assert metrics["MRR"] == 0.5
    assert metrics["nDCG@5"] > 0
```

- [ ] **Step 2: 运行测试并确认查询文件和脚本缺失**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_content_organization_retrieval_eval.py -v`

Expected: FAIL because `retrieval_queries.jsonl` is missing.

- [ ] **Step 3: 为每份真实 UIR 编写至少两条可回答查询**

查询必须引用 UIR 中真实存在的 block ID、标题或关键词。采购查询集合必须包含项目名称、
预算金额、采购人、中标供应商和截止日期；至少包含需要表格和标题上下文才能判定的查询。

- [ ] **Step 4: 实现无 gold 泄漏的检索与指标**

```python
def score_chunk(query: str, chunk: dict[str, Any]) -> float: ...
def rank_chunks(query: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]: ...
def is_relevant(chunk: dict[str, Any], gold: dict[str, Any]) -> bool: ...
def ranking_metrics(relevance: list[bool]) -> dict[str, float]: ...
def evaluate_strategy(...) -> dict[str, Any]: ...
```

`score_chunk()` 只能读取 query、chunk text、title_path 和 keywords；测试通过构造两个仅
source block ID 不同但文本相同的 chunk，断言分数完全相同。

- [ ] **Step 5: 实现五策略 HTTP 编排和双格式报告**

策略参数由固定字典生成。报告包含 Summary、Strategy Comparison、Per Document Type、
Per Query Failure Cases、Chunk Quality Statistics 和 Recommendation。

- [ ] **Step 6: 运行检索测试**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_content_organization_retrieval_eval.py -v`

Expected: PASS including empty chunks and report generation cases.

- [ ] **Step 7: 提交检索评测**

```powershell
git add examples/real_world/gold/retrieval_queries.jsonl scripts/eval_content_organization_retrieval.py backend/tests/test_content_organization_retrieval_eval.py
git commit -m "feat: evaluate content organization retrieval"
```

### Task 6: 实现真实人审知识闭环评测

**Files:**
- Create: `backend/tests/test_real_world_knowledge_loop.py`
- Create: `scripts/eval_knowledge_loop_real_world.py`

- [ ] **Step 1: 写闭环不变量失败测试**

使用临时 SQLite、临时 storage 和 FastAPI `TestClient`：

```python
def test_draft_pack_does_not_affect_effective_template(client) -> None:
    before = client.get(
        "/api/v1/knowledge/effective-template",
        params={"schema_id": "procurement_doc", "template_id": "procurement_doc_base_v1"},
    ).json()
    pack = create_pack_from_accepted_candidate(client)
    draft = client.get(
        "/api/v1/knowledge/effective-template",
        params={"schema_id": "procurement_doc", "template_id": "procurement_doc_base_v1"},
    ).json()
    assert draft == before
    client.post(f"/api/v1/knowledge/packs/{pack['pack_id']}/activate").raise_for_status()
    active = client.get(
        "/api/v1/knowledge/effective-template",
        params={"schema_id": "procurement_doc", "template_id": "procurement_doc_base_v1"},
    ).json()
    assert active != before
```

另写旧任务 execution snapshot 激活前后字节相同，以及 forbidden badcase 产生 blocked
candidate、accept 返回 422 的测试。

- [ ] **Step 2: 运行闭环测试并确认脚本编排缺失**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_real_world_knowledge_loop.py -v`

Expected: FAIL while loading `eval_knowledge_loop_real_world`.

- [ ] **Step 3: 实现知识闭环 HTTP 客户端方法**

扩展 `EvaluationHttpClient`：

```python
def list_reviews(self, status: str) -> list[dict[str, Any]]: ...
def approve_review(self, review_id: str) -> dict[str, Any]: ...
def list_candidates(self) -> list[dict[str, Any]]: ...
def accept_candidate(self, candidate_id: str) -> dict[str, Any]: ...
def create_pack(self, schema_id: str, template_id: str) -> dict[str, Any]: ...
def activate_pack(self, pack_id: str) -> dict[str, Any]: ...
def effective_template(self, schema_id: str, template_id: str) -> dict[str, Any]: ...
def knowledge_metrics(self) -> dict[str, Any]: ...
```

- [ ] **Step 4: 实现闭环 CLI 和报告**

选取 gold 中可批准且非 badcase 的至少三个 review，执行 approve、candidate accept、
draft pack、draft effective-template 检查、activate 和新任务重跑。缓存旧 snapshot 和
mapping report，激活后重新获取并逐值比较。

输出 before/after recall、required coverage、批准数、候选数、active pack 数、
badcase 违规数和 `old_snapshot_unchanged`，Markdown 包含设计要求的七个章节。

- [ ] **Step 5: 运行闭环测试**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_real_world_knowledge_loop.py tests/test_review_knowledge_api.py tests/test_review_knowledge_services.py -v`

Expected: PASS.

- [ ] **Step 6: 提交闭环评测**

```powershell
git add scripts/eval_support.py scripts/eval_knowledge_loop_real_world.py backend/tests/test_real_world_knowledge_loop.py
git commit -m "feat: evaluate real-world review knowledge loop"
```

### Task 7: 生成真实报告并如实处理未达标项

**Files:**
- Create: `reports/real_world_mapping_eval_report.json`
- Create: `reports/real_world_mapping_eval_report.md`
- Create: `reports/procurement_doc_eval_report.json`
- Create: `reports/procurement_doc_eval_report.md`
- Create: `reports/content_organization_retrieval_eval.json`
- Create: `reports/content_organization_retrieval_eval.md`
- Create: `reports/knowledge_loop_eval_report.json`
- Create: `reports/knowledge_loop_eval_report.md`

- [ ] **Step 1: 创建唯一临时数据库和存储并初始化**

```powershell
$token = [Guid]::NewGuid().ToString("N")
$env:DATABASE_URL = "sqlite:///F:/p2/backend/topic5_eval_$token.db"
$env:STORAGE_ROOT = "F:/p2/backend/topic5_storage_$token"
.\backend\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from app.database import init_db; init_db()"
```

- [ ] **Step 2: 启动隐藏 Uvicorn 并运行四个 CLI**

```powershell
.\backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000
.\backend\.venv\Scripts\python.exe scripts\eval_procurement_doc.py --base-url http://127.0.0.1:8000
.\backend\.venv\Scripts\python.exe scripts\eval_content_organization_retrieval.py --base-url http://127.0.0.1:8000
.\backend\.venv\Scripts\python.exe scripts\eval_knowledge_loop_real_world.py --base-url http://127.0.0.1:8000
```

Uvicorn 用 `Start-Process -WindowStyle Hidden` 启动，并在 `finally` 中 `Stop-Process`。

- [ ] **Step 3: 校验报告契约和真实阈值**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_real_world_mapping_eval.py tests/test_procurement_catalog.py tests/test_content_organization_retrieval_eval.py tests/test_real_world_knowledge_loop.py -v`

Expected: PASS. 若推荐指标未达到，不改写指标；在 Markdown Recommendation/Remaining
Issues 中记录真实失败原因。

- [ ] **Step 4: 提交可复现报告**

```powershell
git add reports/real_world_mapping_eval_report.* reports/procurement_doc_eval_report.* reports/content_organization_retrieval_eval.* reports/knowledge_loop_eval_report.*
git commit -m "docs: add topic 5 evaluation evidence"
```

### Task 8: 更新交付文档

**Files:**
- Modify: `README.md`
- Modify: `docs/real_world_uir_dataset.md`
- Modify: `docs/requirement_mapping.md`
- Modify: `docs/final_demo_script.md`
- Modify: `docs/final_handoff_status.md`

- [ ] **Step 1: 写文档引用测试**

在 `backend/tests/test_real_world_mapping_eval.py` 增加：

```python
def test_handoff_docs_reference_all_four_reports() -> None:
    required = {
        "reports/real_world_mapping_eval_report.md",
        "reports/procurement_doc_eval_report.md",
        "reports/content_organization_retrieval_eval.md",
        "reports/knowledge_loop_eval_report.md",
    }
    text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "README.md",
            "docs/real_world_uir_dataset.md",
            "docs/requirement_mapping.md",
            "docs/final_demo_script.md",
            "docs/final_handoff_status.md",
        )
    )
    assert required <= {item for item in required if item in text}
```

- [ ] **Step 2: 运行测试并确认引用缺失**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_real_world_mapping_eval.py::test_handoff_docs_reference_all_four_reports -v`

Expected: FAIL because the four new report paths are not documented.

- [ ] **Step 3: 更新五份文档**

README 只增加四项摘要和详细文档链接；数据集文档解释两个 gold 文件和采购 catalog；
requirement mapping 增加四项证据表；demo script 增加四个 CLI 演示顺序；handoff status
记录已完成项、真实指标和以下限制：

```text
- Retrieval evaluator is lightweight and is not a full RAG system.
- Procurement schema is v1 and aliases require continued real-sample review.
- Gold labels are coursework-scale evaluation labels, not an enterprise benchmark.
```

- [ ] **Step 4: 运行文档引用测试**

Run: `cd backend; .\.venv\Scripts\python -m pytest tests/test_real_world_mapping_eval.py::test_handoff_docs_reference_all_four_reports -v`

Expected: PASS.

- [ ] **Step 5: 提交文档**

```powershell
git add README.md docs/real_world_uir_dataset.md docs/requirement_mapping.md docs/final_demo_script.md docs/final_handoff_status.md backend/tests/test_real_world_mapping_eval.py
git commit -m "docs: document topic 5 evaluation deepening"
```

### Task 9: 全量验证与验收核对

**Files:**
- Verify only

- [ ] **Step 1: 运行专项测试**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_real_world_mapping_eval.py tests/test_procurement_catalog.py tests/test_content_organization_retrieval_eval.py tests/test_real_world_knowledge_loop.py -q
```

Expected: all specialized tests pass.

- [ ] **Step 2: 运行后端完整测试和 Ruff**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
```

Expected: zero failures and `All checks passed!`.

- [ ] **Step 3: 运行前端构建**

Run: `cd frontend; npm run build`

Expected: TypeScript and Vite build exit 0.

- [ ] **Step 4: 运行总验证和 OpenAPI 检查**

Run: `.\backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi`

Expected: backend tests, Ruff, frontend build and OpenAPI export all exit 0.

- [ ] **Step 5: 对照设计逐项读取四份 JSON 报告**

确认：

```text
real_world_mapping_eval.document_count >= 16
real_world_mapping_eval.package_pass_rate == 1.0
real_world_mapping_eval.badcase_violation_count == 0
knowledge_loop_eval.old_snapshot_unchanged is true
knowledge_loop_eval.badcase_violation_count == 0
```

采购提升和结构化检索提升若未达到推荐值，最终交付必须报告实际值和报告中的原因。

- [ ] **Step 6: 检查工作树范围**

Run: `git status --short`

Expected: 只保留用户提供但未纳入提交的
`docs/guildline/课题5四项深化实施指导文档.md`，没有评测临时数据库或存储目录。
