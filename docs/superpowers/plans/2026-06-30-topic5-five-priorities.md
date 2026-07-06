# SchemaPack Agent 五优先级深化 Implementation Plan

> **Historical plan:** Preserved as an execution record. Current status: [`../../project_status.md`](../../交接/project_status.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 连续落实课题 5 五优先级指导文档，提升非采购映射与严格验证，扩展真实 UIR 数据集，增加内容质量和知识成长评测，并证明成果包可被下游消费。

**Architecture:** 复用现有生产服务和 `scripts/eval_support.py`，以单职责 CLI 和可测试纯函数补齐能力；合法单样本失败写入报告，输入、引用和基础设施错误快速失败。所有新增生产行为严格遵循 TDD，最终由真实 HTTP 评测、JSON/Markdown 报告和统一质量门禁共同验收。

**Tech Stack:** Python 3.12、FastAPI、Pydantic、SQLAlchemy、pytest、Ruff、React、TypeScript、Vite、Vitest、JSON/JSONL、CSV、SQLite。

---

## File Structure

### 新增脚本

- `scripts/analyze_real_world_validation_gaps.py`：只读聚合现有映射与验证失败。
- `scripts/eval_non_procurement_doc.py`：执行 general/meeting/policy 专项 HTTP 评测。
- `scripts/build_real_world_dataset_inventory.py`：交叉校验 manifest、UIR 和 gold。
- `scripts/eval_content_strategy_comparison.py`：比较五种 chunk 策略。
- `scripts/eval_summary_faithfulness.py`：确定性检查摘要事实支持度。
- `scripts/eval_content_tag_quality.py`：计算三类标签指标。
- `scripts/eval_review_knowledge_growth.py`：执行 before/after 知识成长评测。
- `scripts/package_io.py`：统一读取 package 目录或 ZIP，不包含业务规则。
- `scripts/export_structured_csv.py`：导出 long/wide CSV。
- `scripts/export_rag_corpus.py`：导出 RAG JSONL。
- `scripts/verify_downstream_contract.py`：执行消费方合同校验。

### 新增测试

- `backend/tests/test_real_world_validation_gap_analysis.py`
- `backend/tests/test_non_procurement_schema_templates.py`
- `backend/tests/test_general_doc_mapping_rules.py`
- `backend/tests/test_meeting_doc_mapping_rules.py`
- `backend/tests/test_policy_doc_mapping_rules.py`
- `backend/tests/test_real_world_non_procurement_validation.py`
- `backend/tests/test_real_world_dataset_inventory.py`
- `backend/tests/test_content_strategy_comparison.py`
- `backend/tests/test_summary_faithfulness_eval.py`
- `backend/tests/test_content_tag_quality_eval.py`
- `backend/tests/test_review_knowledge_growth.py`
- `backend/tests/test_downstream_exports.py`
- `backend/tests/test_downstream_contract.py`

### 数据、报告与界面

- 修改 `examples/production_like/schemas/{general_doc,meeting_doc,policy_doc}_v1.json`。
- 修改 `examples/production_like/mapping_templates/{general_doc,meeting_doc,policy_doc}_base_v1.json`。
- 扩展 `examples/real_world/sources/source_manifest.json` 和 `examples/real_world/uir/**`。
- 扩展 `examples/real_world/gold/{mapping_gold,real_world_badcases,retrieval_queries}.jsonl`。
- 新增 `examples/real_world/gold/content_organization_gold.jsonl`。
- 新增 `examples/real_world/review_fixtures/next_phase_review_decisions.jsonl`。
- 生成指导文档列出的八组 JSON/Markdown 报告和 baseline 快照。
- 修改 `frontend/src/types.ts`、`frontend/src/api.ts`、`frontend/src/evidence.ts`、
  `frontend/src/evidence.test.ts`，新增聚合报告展示组件并接入 `frontend/src/App.tsx`。
- 更新 README 和课题 5 交付文档。

---

### Task 1: 冻结基线并实现验证差距分析

**Files:**
- Create: `scripts/analyze_real_world_validation_gaps.py`
- Create: `backend/tests/test_real_world_validation_gap_analysis.py`
- Create: `reports/baselines/next_phase_before/*.json`
- Create: `reports/real_world_validation_gap_analysis.json`
- Create: `reports/real_world_validation_gap_analysis.md`

- [ ] **Step 1: 复制现有五份报告到 baseline 目录**

Run:

```powershell
New-Item -ItemType Directory -Force reports\baselines\next_phase_before
Copy-Item reports\real_world_eval_report.json reports\baselines\next_phase_before\
Copy-Item reports\real_world_mapping_eval_report.json reports\baselines\next_phase_before\
Copy-Item reports\procurement_doc_eval_report.json reports\baselines\next_phase_before\
Copy-Item reports\content_organization_retrieval_eval.json reports\baselines\next_phase_before\
Copy-Item reports\real_world_knowledge_loop_report.json reports\baselines\next_phase_before\
```

Expected: five immutable JSON snapshots exist; no production logic changes.

- [ ] **Step 2: 写聚合与报告的失败测试**

```python
def test_analyze_groups_missing_and_review_fields_by_doc_type(tmp_path):
    module = load_script("analyze_real_world_validation_gaps.py")
    items = [
        {
            "doc_id": "g1",
            "doc_type": "general_doc",
            "strict_validation_passed": False,
            "required_missing": ["content"],
            "review_required_targets": ["category"],
            "badcase_violations": [],
        }
    ]
    report = module.build_gap_report(items)
    assert report["summary"]["strict_failed_count"] == 1
    assert report["by_doc_type"]["general_doc"]["top_missing_required_fields"] == [
        {"field": "content", "count": 1}
    ]
    assert report["by_doc_type"]["general_doc"]["top_review_required_fields"] == [
        {"field": "category", "count": 1}
    ]
```

- [ ] **Step 3: 运行测试并确认 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_real_world_validation_gap_analysis.py -q
```

Expected: FAIL because `scripts/analyze_real_world_validation_gaps.py` does not exist.

- [ ] **Step 4: 实现最小差距分析接口**

```python
def build_gap_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_doc_type: dict[str, dict[str, Any]] = {}
    field_failures: list[dict[str, Any]] = []
    for doc_type in ("general_doc", "meeting_doc", "policy_doc", "procurement_doc"):
        rows = [row for row in items if row["doc_type"] == doc_type]
        missing = Counter(field for row in rows for field in row.get("required_missing", []))
        review = Counter(
            field for row in rows for field in row.get("review_required_targets", [])
        )
        by_doc_type[doc_type] = {
            "doc_count": len(rows),
            "strict_pass": sum(bool(row.get("strict_validation_passed")) for row in rows),
            "strict_failed": sum(not bool(row.get("strict_validation_passed")) for row in rows),
            "top_missing_required_fields": counter_rows(missing),
            "top_review_required_fields": counter_rows(review),
        }
    return {
        "summary": summarize(items),
        "by_doc_type": by_doc_type,
        "field_failures": field_failures,
    }
```

CLI 默认读取 `reports/real_world_mapping_eval_report.json` 和
`reports/real_world_packages/**/{validation_report,mapping_report}.json`，输出固定
JSON/Markdown；报告列出 alias、regex、保留复核和禁止修改建议。

- [ ] **Step 5: 运行测试并生成报告**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_real_world_validation_gap_analysis.py -q
backend\.venv\Scripts\python.exe scripts\analyze_real_world_validation_gaps.py
```

Expected: tests PASS; both gap report files exist and record 11 baseline strict failures.

- [ ] **Step 6: 提交 Phase A**

```powershell
git add scripts/analyze_real_world_validation_gaps.py backend/tests/test_real_world_validation_gap_analysis.py reports/baselines/next_phase_before reports/real_world_validation_gap_analysis.json reports/real_world_validation_gap_analysis.md
git commit -m "feat: analyze real-world validation gaps"
```

---

### Task 2: 强化三类非采购 Schema 和 Template

**Files:**
- Modify: `examples/production_like/schemas/general_doc_v1.json`
- Modify: `examples/production_like/schemas/meeting_doc_v1.json`
- Modify: `examples/production_like/schemas/policy_doc_v1.json`
- Modify: `examples/production_like/mapping_templates/general_doc_base_v1.json`
- Modify: `examples/production_like/mapping_templates/meeting_doc_base_v1.json`
- Modify: `examples/production_like/mapping_templates/policy_doc_base_v1.json`
- Create: `backend/tests/test_non_procurement_schema_templates.py`
- Create: `backend/tests/test_general_doc_mapping_rules.py`
- Create: `backend/tests/test_meeting_doc_mapping_rules.py`
- Create: `backend/tests/test_policy_doc_mapping_rules.py`

- [ ] **Step 1: 写 catalog 合法性和安全门槛失败测试**

```python
@pytest.mark.parametrize("schema_id", ["general_doc", "meeting_doc", "policy_doc"])
def test_non_procurement_template_targets_exist(schema_id):
    schema = TargetSchema.model_validate(load_schema(schema_id))
    template = MappingTemplate.model_validate(load_template(schema_id))
    targets = {field.field_id for field in schema.fields}
    assert set(template.aliases) <= targets
    assert all(rule.target_field_id in targets for rule in template.regex_rules)

def test_required_fields_remain_semantically_minimal():
    assert required("general_doc") == {"title", "content"}
    assert required("meeting_doc") == {"meeting_title", "meeting_date", "content"}
    assert required("policy_doc") == {"title", "issuer", "publish_date", "content"}
```

行为测试分别断言：

```python
assert accepted_target("办事指南", "文档类型") == "document_subtype"
assert accepted_target("2025年7月12日下午", "会议时间") == "meeting_date"
assert accepted_target("工业和信息化部", "发文机关") == "issuer"
assert forbidden_auto_mapping("预算金额", "category")
assert forbidden_auto_mapping("会议编号", "meeting_title")
assert forbidden_auto_mapping("解读发布时间", "publish_date")
```

- [ ] **Step 2: 运行四组测试并确认 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_non_procurement_schema_templates.py backend/tests/test_general_doc_mapping_rules.py backend/tests/test_meeting_doc_mapping_rules.py backend/tests/test_policy_doc_mapping_rules.py -q
```

Expected: FAIL on missing fields/aliases and current mapping behavior.

- [ ] **Step 3: 扩展 general_doc**

保留 `title`、`content` 为 required；增加：

```json
{
  "field_id": "document_subtype",
  "name": "document_subtype",
  "display_name": "文档子类型",
  "type": "enum",
  "required": false,
  "aliases": ["文档类型", "指南类型", "事项类型"],
  "constraints": {
    "enum": ["service_guide", "project_guide", "application_flow", "notice", "announcement", "manual", "other"]
  }
}
```

同时增加 `issuer`、`published_at`、`summary`、`service_object`、
`application_conditions`、`application_materials`、`process_steps`、`deadline`、
`contact`、`attachments` 等 optional 字段；模板补充指导文档中的稳定同义词和
日期/联系方式正则，金额与宽泛 category 保持复核。

- [ ] **Step 4: 扩展 meeting_doc**

保留现有 required；增加 `meeting_number`、`meeting_location`、`chairperson`、
`departments`、`agenda_items`、`decision_items`、`responsible_units`、
`deadlines`、`source`。模板接受“召开日期/会议时间/主持人/审议事项/议定事项”等
明确标签，将日期规范为 `YYYY-MM-DD`；编号、页眉和发文号不得映射成标题。

- [ ] **Step 5: 扩展 policy_doc**

保留现有 required；增加 `document_number`、`policy_level`、`applicable_region`、
`target_audience`、`policy_measures`、`responsible_departments`、
`valid_until`、`source`。模板接受“制定机关/印发机关/成文日期/施行日期”等明确
标签；解读页日期、引用政策日期和附件日期不得自动映射为发布日期。

- [ ] **Step 6: 运行测试和非采购回归**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_non_procurement_schema_templates.py backend/tests/test_general_doc_mapping_rules.py backend/tests/test_meeting_doc_mapping_rules.py backend/tests/test_policy_doc_mapping_rules.py backend/tests/test_procurement_mapping.py -q
backend\.venv\Scripts\python.exe -m ruff check .
```

Expected: all focused tests PASS; procurement tests remain green; Ruff clean.

- [ ] **Step 7: 提交 Schema/Template**

```powershell
git add examples/production_like/schemas examples/production_like/mapping_templates backend/tests/test_non_procurement_schema_templates.py backend/tests/test_general_doc_mapping_rules.py backend/tests/test_meeting_doc_mapping_rules.py backend/tests/test_policy_doc_mapping_rules.py
git commit -m "feat: strengthen non-procurement catalogs"
```

---

### Task 3: 实现非采购专项评测

**Files:**
- Create: `scripts/eval_non_procurement_doc.py`
- Create: `backend/tests/test_real_world_non_procurement_validation.py`
- Create: `reports/non_procurement_doc_eval_report.json`
- Create: `reports/non_procurement_doc_eval_report.md`

- [ ] **Step 1: 写报告契约失败测试**

```python
def test_build_report_summarizes_each_non_procurement_type():
    report = module.build_report([
        result("general_doc", strict=True, recall=1.0),
        result("meeting_doc", strict=False, recall=0.5),
        result("policy_doc", strict=True, recall=0.75),
    ])
    assert report["summary"]["document_count"] == 3
    assert report["by_doc_type"]["general_doc"]["strict_pass_count"] == 1
    assert report["by_doc_type"]["meeting_doc"]["strict_pass_count"] == 0
    assert report["summary"]["badcase_violation_count"] == 0
```

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_real_world_non_procurement_validation.py -q
```

Expected: FAIL because CLI is missing.

- [ ] **Step 3: 实现评测**

复用 `EvaluationHttpClient` 和 `eval_real_world_mapping.evaluate_rows`：

```python
CATALOGS = {
    "general_doc": ("general_doc", "general_doc_base_v1"),
    "meeting_doc": ("meeting_doc", "meeting_doc_base_v1"),
    "policy_doc": ("policy_doc", "policy_doc_base_v1"),
}

def build_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "summary": aggregate(items),
        "by_doc_type": {
            doc_type: aggregate([item for item in items if item["doc_type"] == doc_type])
            for doc_type in CATALOGS
        },
        "documents": items,
        "thresholds": {
            "general_doc": 2,
            "meeting_doc": 2,
            "policy_doc": 3,
            "mapping_recall": 0.65,
        },
    }
```

逐文档记录 strict pass、required missing、mapping recall、review-required、
high-risk auto accepted、badcase 和 package verification。

- [ ] **Step 4: 运行测试**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_real_world_non_procurement_validation.py backend/tests/test_real_world_mapping_eval.py -q
```

Expected: PASS.

- [ ] **Step 5: 启动隔离后端并生成真实报告**

Run:

```powershell
$env:DATABASE_URL='sqlite:///./reports/non_procurement_eval.db'
$env:STORAGE_ROOT='reports/non_procurement_eval_storage'
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_doc.py --base-url http://127.0.0.1:8000 --timeout 60
```

Expected: report contains 11 non-procurement documents, actual thresholds, and zero hidden failures.

- [ ] **Step 6: 提交专项评测**

```powershell
git add scripts/eval_non_procurement_doc.py backend/tests/test_real_world_non_procurement_validation.py reports/non_procurement_doc_eval_report.json reports/non_procurement_doc_eval_report.md
git commit -m "feat: evaluate non-procurement documents"
```

---

### Task 4: 扩展真实 UIR 数据集到至少 30 份

**Files:**
- Modify: `examples/real_world/sources/source_manifest.json`
- Modify: `examples/real_world/uir/**`
- Modify: `backend/tests/test_real_world_uir_tools.py`

- [ ] **Step 1: 写数据规模与来源契约失败测试**

```python
def test_real_world_dataset_has_at_least_thirty_official_sources():
    manifest = load_manifest()
    assert len(manifest["items"]) >= 30
    assert all(item["source_url"].startswith("https://") for item in manifest["items"])
    assert all(item["license_note"] for item in manifest["items"])
    assert all(item["source_site"] for item in manifest["items"])
```

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_real_world_uir_tools.py::test_real_world_dataset_has_at_least_thirty_official_sources -q
```

Expected: FAIL with current count 16.

- [ ] **Step 3: 在 manifest 增加以下 14 个具体官方来源**

| ID | 类型 | 官方 URL |
| --- | --- | --- |
| `real_policy_006_technology_incubator_rules` | policy | `https://www.miit.gov.cn/zwgk/zcwj/wjfb/tz/art/2025/art_3a170b97d16c43ce8d2d6f7a67e9e60e.html` |
| `real_policy_007_one_thing_list` | policy | `https://app.www.gov.cn/govdata/gov/202501/16/523725/article.html` |
| `real_policy_008_sme_leader_training` | policy | `https://www.miit.gov.cn/zwgk/zcwj/wjfb/tz/art/2025/art_19d8e5b426f540699e5fe07a816a7493.html` |
| `real_policy_009_network_safety_work` | policy | `https://www.miit.gov.cn/zwgk/zcwj/wjfb/tz/art/2025/art_7c2bbce8116a48aab7bc2bda327d1be3.html` |
| `real_procurement_006_vaccine_tender` | procurement | `https://www.ccgp.gov.cn/cggg/zygg/gkzb/202501/t20250117_24080663.htm` |
| `real_procurement_007_testing_equipment_award` | procurement | `https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202509/t20250919_25383556.htm` |
| `real_procurement_008_desktop_award` | procurement | `https://www.ccgp.gov.cn/cggg/zygg/zbgg/202506/t20250616_24783596.htm` |
| `real_procurement_009_pollutant_monitoring_award` | procurement | `https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202504/t20250427_24507229.htm` |
| `real_procurement_010_ultrasound_award` | procurement | `https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202504/t20250407_24404253.htm` |
| `real_meeting_004_kundulun_minutes` | meeting | `https://www.kdl.gov.cn/detail/cid/1906/aid/125748` |
| `real_meeting_005_yongtai_minutes` | meeting | `https://www.yongtai.gov.cn/xjwz/zwgk/zcfg/202507/P020250801603701924056.pdf` |
| `real_meeting_006_shandan_minutes` | meeting | `https://www.shandan.gov.cn/zfxxgk/fdzdgknr/xzfhy/xzfcwhy/202511/W020251120606165226334.pdf` |
| `real_general_004_tianhe_service_guide` | general | `https://www.gz.gov.cn/interf/storage/material/2026/01/20/0ebc48ad0dfd3b325bf2cf024e72a42b.pdf` |
| `real_policy_010_auto_ota_management` | policy | `https://www.miit.gov.cn/jgsj/zbys/wjfb/art/2025/art_fa604619ed45484386f37422d01f5527.html` |

每项初始状态为 `planned`，填入 title、source_site、source_format、license_note、
notes 和目标 `uir_path`。若某来源在执行时不可访问或内容类型变化，记录失败原因，
从同一官方站点选择语义等价替代来源并在 manifest 中保留替换说明。

- [ ] **Step 4: 采集并构建新增 UIR**

Run:

```powershell
backend\.venv\Scripts\python.exe scripts\collect_real_world_sources.py
backend\.venv\Scripts\python.exe scripts\build_real_world_uir.py
backend\.venv\Scripts\python.exe scripts\validate_real_world_uir.py
```

Expected: at least 30 manifest entries have `status=extracted`; all UIR validate; no OCR path used.

- [ ] **Step 5: 检查每份新增 UIR 的字段与 source block**

每份必须满足：

```text
uir_version = 1.0
doc_id == manifest.source_id
metadata.source_url == manifest.source_url
metadata.source_sha256 == manifest.source_sha256
blocks 非空且 block_id 唯一
source_format 仅 html 或 pdf
```

- [ ] **Step 6: 运行数据工具测试并提交**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_real_world_uir_tools.py -q
```

```powershell
git add examples/real_world/sources/source_manifest.json examples/real_world/uir backend/tests/test_real_world_uir_tools.py
git commit -m "data: expand official real-world UIR dataset"
```

---

### Task 5: 补齐扩展数据集的 gold、badcase、query 和 inventory

**Files:**
- Modify: `examples/real_world/gold/mapping_gold.jsonl`
- Modify: `examples/real_world/gold/real_world_badcases.jsonl`
- Modify: `examples/real_world/gold/retrieval_queries.jsonl`
- Create: `scripts/build_real_world_dataset_inventory.py`
- Create: `backend/tests/test_real_world_dataset_inventory.py`
- Create: `reports/real_world_dataset_inventory.json`
- Create: `reports/real_world_dataset_inventory.md`

- [ ] **Step 1: 写交叉引用和 inventory 失败测试**

```python
def test_inventory_requires_gold_and_queries_for_every_uir():
    report = module.build_inventory(dataset_paths(ROOT / "examples/real_world"))
    assert report["summary"]["uir_count"] >= 30
    assert report["summary"]["missing_mapping_gold"] == 0
    assert report["summary"]["missing_retrieval_queries"] == 0
    assert report["summary"]["orphan_manifest_items"] == 0
```

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_real_world_dataset_inventory.py -q
```

Expected: FAIL because inventory script and new gold rows are absent.

- [ ] **Step 3: 为 14 份新增 UIR 添加人工 gold**

每份 mapping row 至少包含 title/content 和两个类型特有字段；每份至少两个 retrieval
query；每类新增文档至少一个 high-risk badcase。所有 `source_path` 和
`relevant_source_block_ids` 必须指向实际 UIR 内容，禁止用期望答案参与排序。

- [ ] **Step 4: 实现 inventory**

```python
def build_inventory(paths: dict[str, Path]) -> dict[str, Any]:
    manifest = read_json(paths["manifest"])
    uirs = load_uirs(paths["uir_dir"])
    mappings = load_jsonl(paths["mapping_gold"])
    badcases = load_jsonl(paths["badcases"])
    queries = load_jsonl(paths["queries"])
    return {
        "summary": cross_reference(manifest, uirs, mappings, queries),
        "by_doc_type": distribution(uirs, mappings, badcases, queries),
        "field_density": field_density(uirs),
        "issues": find_issues(manifest, uirs, mappings, badcases, queries),
    }
```

- [ ] **Step 5: 运行测试并生成 inventory**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_real_world_dataset_inventory.py backend/tests/test_real_world_mapping_eval.py -q
backend\.venv\Scripts\python.exe scripts\build_real_world_dataset_inventory.py
```

Expected: at least 30 UIR, no orphan references, no missing gold/query coverage.

- [ ] **Step 6: 提交数据质量证据**

```powershell
git add examples/real_world/gold scripts/build_real_world_dataset_inventory.py backend/tests/test_real_world_dataset_inventory.py reports/real_world_dataset_inventory.json reports/real_world_dataset_inventory.md
git commit -m "feat: inventory expanded real-world dataset"
```

---

### Task 6: 实现 chunk 策略对比评测

**Files:**
- Create: `examples/real_world/gold/content_organization_gold.jsonl`
- Create: `scripts/eval_content_strategy_comparison.py`
- Create: `backend/tests/test_content_strategy_comparison.py`
- Create: `reports/content_strategy_comparison_report.json`
- Create: `reports/content_strategy_comparison_report.md`

- [ ] **Step 1: 写 gold 和指标失败测试**

```python
def test_strategy_metrics_penalize_split_tables_and_duplicate_text():
    metrics = module.evaluate_chunks(
        chunks=[chunk("c1", ["b1"]), chunk("c2", ["b1"])],
        gold={"required_block_groups": [["b1", "b2"]], "table_block_ids": ["b2"]},
    )
    assert metrics["duplicate_rate"] > 0
    assert metrics["required_group_coverage"] < 1
    assert metrics["table_split_violation_count"] == 1
```

- [ ] **Step 2: 运行并确认 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_content_strategy_comparison.py -q
```

Expected: FAIL because gold and script are missing.

- [ ] **Step 3: 添加至少 20 份文档的内容组织 gold**

每行使用：

```json
{
  "doc_id": "real_policy_001_training_platform_rules",
  "required_block_groups": [["real_policy_001_training_platform_rules_b001", "real_policy_001_training_platform_rules_b002"]],
  "table_block_ids": [],
  "expected_title_paths": ["总则"],
  "summary_facts": ["全国校外教育培训监管与服务综合平台"],
  "expected_tags": {
    "content": ["policy"],
    "management": ["official_source"],
    "quality": ["source_linked"]
  }
}
```

- [ ] **Step 4: 实现五策略比较**

比较 `fixed_window`、`heading_aware`、`source_block_aware`、`table_protect`、
`parent_child`，输出 required group coverage、block coverage、duplicate rate、
table split violations、source-link coverage、平均 chunks/token 及现有检索指标。

- [ ] **Step 5: 运行测试并生成报告**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_content_strategy_comparison.py -q
backend\.venv\Scripts\python.exe scripts\eval_content_strategy_comparison.py
```

Expected: five strategies appear in both reports; failures retain document and block evidence.

- [ ] **Step 6: 提交策略评测**

```powershell
git add examples/real_world/gold/content_organization_gold.jsonl scripts/eval_content_strategy_comparison.py backend/tests/test_content_strategy_comparison.py reports/content_strategy_comparison_report.json reports/content_strategy_comparison_report.md
git commit -m "feat: compare content organization strategies"
```

---

### Task 7: 实现摘要忠实度和标签质量评测

**Files:**
- Create: `scripts/eval_summary_faithfulness.py`
- Create: `scripts/eval_content_tag_quality.py`
- Create: `backend/tests/test_summary_faithfulness_eval.py`
- Create: `backend/tests/test_content_tag_quality_eval.py`
- Create: `reports/summary_faithfulness_eval_report.json`
- Create: `reports/summary_faithfulness_eval_report.md`
- Create: `reports/content_tag_quality_eval_report.json`
- Create: `reports/content_tag_quality_eval_report.md`

- [ ] **Step 1: 写摘要事实支持失败测试**

```python
def test_summary_flags_unsupported_number_and_entity():
    result = module.evaluate_summary(
        source_text="项目预算为100万元，由甲单位负责。",
        summary="项目预算为200万元，由乙单位负责。",
    )
    assert result["unsupported_numbers"] == ["200万元"]
    assert "乙单位" in result["unsupported_entities"]
    assert result["faithful"] is False
```

- [ ] **Step 2: 写标签 precision/recall 失败测试**

```python
def test_tag_metrics_are_computed_per_category():
    report = module.build_report(
        [{"expected": {"content": ["policy"]}, "actual": {"content": ["policy", "notice"]}}]
    )
    assert report["content"]["precision"] == 0.5
    assert report["content"]["recall"] == 1.0
```

- [ ] **Step 3: 运行并确认 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_summary_faithfulness_eval.py backend/tests/test_content_tag_quality_eval.py -q
```

Expected: FAIL because both scripts are missing.

- [ ] **Step 4: 实现确定性摘要检查**

提取来源和摘要中的日期、金额、百分比、编号和机构实体；摘要事实必须能在对应来源
block 中找到规范化匹配。输出 `supported_facts`、`unsupported_numbers`、
`unsupported_dates`、`unsupported_entities`、`needs_human_review` 和逐文档分数。

- [ ] **Step 5: 实现标签指标**

按 content/management/quality 分别计算 micro/macro precision、recall、F1，
并输出 missing/unexpected tag 明细。管理标签只验证可从 package metadata 推导的值，
质量标签只验证 source links、review 状态和 chunk 质量证据。

- [ ] **Step 6: 运行测试并生成报告**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_summary_faithfulness_eval.py backend/tests/test_content_tag_quality_eval.py -q
backend\.venv\Scripts\python.exe scripts\eval_summary_faithfulness.py
backend\.venv\Scripts\python.exe scripts\eval_content_tag_quality.py
```

Expected: tests PASS; both report pairs exist; no model-generated judgment.

- [ ] **Step 7: 提交内容质量评测**

```powershell
git add scripts/eval_summary_faithfulness.py scripts/eval_content_tag_quality.py backend/tests/test_summary_faithfulness_eval.py backend/tests/test_content_tag_quality_eval.py reports/summary_faithfulness_eval_report.json reports/summary_faithfulness_eval_report.md reports/content_tag_quality_eval_report.json reports/content_tag_quality_eval_report.md
git commit -m "feat: evaluate summary and tag quality"
```

---

### Task 8: 实现人审知识能力成长曲线

**Files:**
- Create: `examples/real_world/review_fixtures/next_phase_review_decisions.jsonl`
- Create: `scripts/eval_review_knowledge_growth.py`
- Create: `backend/tests/test_review_knowledge_growth.py`
- Create: `reports/review_knowledge_growth_report.json`
- Create: `reports/review_knowledge_growth_report.md`

- [ ] **Step 1: 写状态与安全不变量失败测试**

```python
def test_growth_report_requires_improvement_and_snapshot_safety():
    report = module.build_growth_report(
        before={"mapping_recall": 0.5, "review_required_count": 4},
        after={"mapping_recall": 0.75, "review_required_count": 2},
        old_snapshot_unchanged=True,
        badcase_violation_count=0,
        rejected_candidate_activated_count=0,
    )
    assert report["delta"]["mapping_recall"] == 0.25
    assert report["delta"]["review_required_count"] == -2
    assert report["old_snapshot_unchanged"] is True
```

- [ ] **Step 2: 运行并确认 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_review_knowledge_growth.py -q
```

Expected: FAIL because fixture and script are missing.

- [ ] **Step 3: 编写 review fixture**

至少包含三条 approve、两条 reject 和一条 blocked 决策；每行固定包含：

```json
{
  "decision_id": "next_phase_review_001",
  "doc_id": "real_policy_001_training_platform_rules",
  "target_field_id": "issuer",
  "decision": "approve",
  "candidate_rule": {"kind": "alias", "source_name": "发布机构", "target_field_id": "issuer"},
  "expected_candidate_status": "accepted",
  "expected_pack_effect": true,
  "risk_reason": ""
}
```

- [ ] **Step 4: 实现隔离 before/after 编排**

复用现有 review/knowledge HTTP 客户端方法。保存 before 快照，逐项应用 fixture，
验证 draft 不生效、reject/blocked 不激活；激活 pack 后运行新任务并重新读取旧任务。
报告必须包含：

```python
{
    "before": before_metrics,
    "after": after_metrics,
    "delta": metric_delta(before_metrics, after_metrics),
    "old_snapshot_unchanged": old_snapshot == reread_snapshot,
    "badcase_violation_count": badcase_violations,
    "rejected_candidate_activated_count": rejected_activated,
}
```

- [ ] **Step 5: 运行测试和真实评测**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_review_knowledge_growth.py backend/tests/test_real_world_knowledge_loop.py -q
backend\.venv\Scripts\python.exe scripts\eval_review_knowledge_growth.py
```

Expected: after recall is greater than before, after review-required is lower, old snapshot true,
badcase zero, rejected activated zero.

- [ ] **Step 6: 提交成长曲线**

```powershell
git add examples/real_world/review_fixtures/next_phase_review_decisions.jsonl scripts/eval_review_knowledge_growth.py backend/tests/test_review_knowledge_growth.py reports/review_knowledge_growth_report.json reports/review_knowledge_growth_report.md
git commit -m "feat: evaluate review knowledge growth"
```

---

### Task 9: 实现 package 读取与结构化 CSV 导出

**Files:**
- Create: `scripts/package_io.py`
- Create: `scripts/export_structured_csv.py`
- Create: `backend/tests/test_downstream_exports.py`

- [ ] **Step 1: 写 ZIP/目录 long CSV 失败测试**

```python
@pytest.mark.parametrize("as_zip", [False, True])
def test_export_structured_csv_reads_package_directory_and_zip(tmp_path, as_zip):
    package = make_package(tmp_path, as_zip=as_zip)
    rows = export_module.export_rows(package, mode="long")
    assert rows[0]["schema_id"] == "policy_doc"
    assert rows[0]["field_name"] == "title"
    assert rows[0]["source_block_ids"] == "b1"
    assert rows[0]["review_required"] == "false"
```

- [ ] **Step 2: 运行并确认 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_downstream_exports.py -q
```

Expected: FAIL because scripts are missing.

- [ ] **Step 3: 实现只读 package 抽象**

```python
@contextmanager
def open_package(path: Path) -> Iterator[PackageReader]:
    if path.is_dir():
        yield DirectoryPackageReader(path)
    elif path.suffix.lower() == ".zip":
        with ZipPackageReader(path) as reader:
            yield reader
    else:
        raise ValueError("package must be a directory or .zip")
```

Reader 提供 `exists(name)`、`read_bytes(name)`、`read_json(name)`、
`read_jsonl(name)` 和 `names()`。

- [ ] **Step 4: 实现 CSV 导出**

long 模式固定字段为：

```python
CSV_FIELDS = [
    "package_id", "task_id", "doc_id", "schema_id", "schema_version",
    "template_id", "template_version", "field_id", "field_name",
    "field_value", "field_type", "source_block_ids", "confidence",
    "review_required",
]
```

CLI 接受 `--package`、`--out`、`--mode long|wide`，校验 manifest、metadata 和
canonical/content 可解析，拒绝空导出。

- [ ] **Step 5: 运行测试**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_downstream_exports.py -q
```

Expected: directory/ZIP long export PASS; malformed package fails with explicit message.

- [ ] **Step 6: 提交 CSV adapter**

```powershell
git add scripts/package_io.py scripts/export_structured_csv.py backend/tests/test_downstream_exports.py
git commit -m "feat: export structured package CSV"
```

---

### Task 10: 实现 RAG corpus 导出

**Files:**
- Create: `scripts/export_rag_corpus.py`
- Modify: `backend/tests/test_downstream_exports.py`

- [ ] **Step 1: 写粒度、摘要和来源策略失败测试**

```python
def test_rag_export_filters_child_granularity(tmp_path):
    package = make_package_with_parent_child_chunks(tmp_path)
    rows = rag_module.export_rows(
        package,
        granularity="child",
        include_summary=True,
        include_keywords=True,
        min_chars=1,
    )
    assert {row["metadata"]["granularity"] for row in rows} == {"child"}
    assert rows[0]["metadata"]["parent_chunk_id"] == "parent-1"
```

- [ ] **Step 2: 运行并确认 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_downstream_exports.py::test_rag_export_filters_child_granularity -q
```

Expected: FAIL because RAG exporter is missing.

- [ ] **Step 3: 实现 RAG row**

```python
def rag_row(chunk: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": chunk["chunk_id"],
        "text": chunk["text"],
        "metadata": {
            "package_id": metadata["package_id"],
            "task_id": metadata["task_id"],
            "doc_id": metadata["doc_id"],
            "schema_id": metadata["schema_id"],
            "schema_version": metadata["schema_version"],
            "template_id": metadata["template_id"],
            "template_version": metadata.get("template_version"),
            "title_path": chunk.get("title_path", []),
            "source_block_ids": chunk.get("source_block_ids", []),
            "source_links": chunk.get("source_links", []),
            "content_tags": chunk.get("content_tags", []),
            "management_tags": chunk.get("management_tags", []),
            "quality_tags": chunk.get("quality_tags", []),
            "token_estimate": chunk.get("token_estimate"),
            "granularity": chunk.get("granularity"),
            "parent_chunk_id": chunk.get("parent_chunk_id"),
        },
    }
```

实现指导文档中的全部参数；缺失 source links 默认 warning，指定
`--fail-on-missing-source-links true` 时返回非零。

- [ ] **Step 4: 运行测试并提交**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_downstream_exports.py -q
```

```powershell
git add scripts/export_rag_corpus.py backend/tests/test_downstream_exports.py
git commit -m "feat: export package RAG corpus"
```

---

### Task 11: 实现下游消费合同验证

**Files:**
- Create: `scripts/verify_downstream_contract.py`
- Create: `backend/tests/test_downstream_contract.py`
- Create: `reports/downstream_contract_eval_report.json`
- Create: `reports/downstream_contract_eval_report.md`

- [ ] **Step 1: 写缺失 artifact、hash mismatch 和 empty chunks 失败测试**

```python
@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("remove_metadata", "missing required artifact: metadata.json"),
        ("corrupt_content", "manifest sha256 mismatch: content.json"),
        ("empty_chunks", "chunks.jsonl must contain at least one row"),
    ],
)
def test_contract_rejects_invalid_packages(tmp_path, mutation, error):
    package = mutate_package(make_package(tmp_path), mutation)
    result = module.verify_package(package)
    assert result["passed"] is False
    assert error in result["errors"]
```

- [ ] **Step 2: 运行并确认 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_downstream_contract.py -q
```

Expected: FAIL because verifier is missing.

- [ ] **Step 3: 实现 consumer contract**

required artifacts：

```python
REQUIRED = {
    "manifest.json", "metadata.json", "content.json", "content.md",
    "chunks.jsonl", "canonical.json", "mapping_report.json",
    "validation_report.json", "content_organization_report.json",
    "verifier_report.json",
}
```

逐文件校验 manifest sha256；metadata 必须有 schema/template/task/doc ID；每个 chunk
必须有 `chunk_id`、非空 text 和 source block/link；随后内存执行 CSV 与 RAG 导出。

- [ ] **Step 4: 实现批量模式和报告**

CLI 同时支持 `--package` 与 `--packages-root`；批量模式递归查找
`standard_package.zip`，输出 passed/failed、errors/warnings 和两个导出布尔值。

- [ ] **Step 5: 运行测试并生成报告**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_downstream_contract.py backend/tests/test_downstream_exports.py -q
backend\.venv\Scripts\python.exe scripts\verify_downstream_contract.py --packages-root reports\real_world_packages --out reports\downstream_contract_eval_report.json --markdown reports\downstream_contract_eval_report.md
```

Expected: every current package passes; invalid fixtures fail for the asserted reason.

- [ ] **Step 6: 提交下游证明**

```powershell
git add scripts/verify_downstream_contract.py backend/tests/test_downstream_contract.py reports/downstream_contract_eval_report.json reports/downstream_contract_eval_report.md
git commit -m "feat: verify downstream package contract"
```

---

### Task 12: 接入报告 API 与前端证据展示

**Files:**
- Modify: `backend/app/api/v1/evaluation_reports.py`
- Modify: `backend/tests/test_evaluation_reports_api.py`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/evidence.ts`
- Modify: `frontend/src/evidence.test.ts`
- Create: `frontend/src/components/DeepeningReportPanel.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `docs/openapi.json`

- [ ] **Step 1: 写 allowlist 和前端归一化失败测试**

后端测试断言新八组报告名称可读，任意路径仍返回 404；前端测试：

```typescript
it("normalizes five-priority report summaries", () => {
  expect(summarizeDeepeningReport("non_procurement_doc_eval_report", {
    summary: { strict_pass_count: 7, document_count: 11 }
  })).toEqual({ primary: "7 / 11", status: "measured" });
});
```

- [ ] **Step 2: 运行并确认 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_evaluation_reports_api.py -q
cd frontend
npm.cmd test -- --run src/evidence.test.ts
```

Expected: FAIL because report names/types/helpers are absent.

- [ ] **Step 3: 扩展只读 allowlist 和前端类型**

仅增加固定报告基名，不增加任意文件读取。`DeepeningReportPanel` 展示非采购通过率、
数据集规模、最佳 chunk 策略、摘要忠实度、标签 F1、知识成长 delta 和下游合同结果；
失败样本用 details 展开。

- [ ] **Step 4: 运行前后端测试并导出 OpenAPI**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_evaluation_reports_api.py -q
backend\.venv\Scripts\python.exe scripts\export_openapi.py
cd frontend
npm.cmd test -- --run src/evidence.test.ts
npm.cmd run build
```

Expected: tests PASS, build succeeds; OpenAPI 仅在实际 schema/path 变化时有差异。

- [ ] **Step 5: 提交演示界面**

```powershell
git add backend/app/api/v1/evaluation_reports.py backend/tests/test_evaluation_reports_api.py frontend/src docs/openapi.json
git commit -m "feat: display five-priority evaluation evidence"
```

---

### Task 13: 更新交付文档和 acceptance 聚合

**Files:**
- Modify: `scripts/build_acceptance_report.py`
- Modify: `backend/tests/test_acceptance_report_script.py`
- Modify: `README.md`
- Modify: `docs/交接/requirement_mapping.md`
- Modify: `docs/real_world_uir_dataset.md`
- Modify: `docs/real_world_knowledge_loop.md`
- Modify: `docs/demo_workflow.md`
- Modify: `docs/交接/final_demo_script.md`
- Modify: `docs/交接/final_handoff_status.md`
- Modify: `docs/api_usage_examples.md`
- Modify: `docs/package_spec.md` only if package shape changed

- [ ] **Step 1: 写 acceptance 引用失败测试**

```python
def test_acceptance_report_includes_five_priority_evidence(tmp_path):
    seed_reports(tmp_path)
    report = module.build_acceptance_report(tmp_path)
    assert report["checks"]["non_procurement"]["report_path"].endswith(
        "non_procurement_doc_eval_report.json"
    )
    assert report["checks"]["dataset_inventory"]["summary"]["uir_count"] >= 30
    assert report["checks"]["downstream_contract"]["summary"]["failed_count"] == 0
```

- [ ] **Step 2: 运行并确认 RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_acceptance_report_script.py -q
```

Expected: FAIL because acceptance aggregation does not reference new reports.

- [ ] **Step 3: 扩展 acceptance report**

为八组报告增加只读 evidence check；缺失或未达标显示 `missing/partial/failed`，
不伪造 passed。文档写明具体命令、报告、真实指标和未达目标。

- [ ] **Step 4: 更新文档边界**

README 和交付文档必须明确：

```text
生产 runtime 从 UIR 开始
不支持 runtime OCR 或任意 raw PDF/Word/Excel 解析
RAG 导出是 corpus adapter，不是完整 RAG/vector DB
LLM fallback 只给 review suggestion，永不自动接受
```

- [ ] **Step 5: 运行测试并生成 acceptance**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_acceptance_report_script.py -q
backend\.venv\Scripts\python.exe scripts\build_acceptance_report.py
```

- [ ] **Step 6: 提交文档**

```powershell
git add scripts/build_acceptance_report.py backend/tests/test_acceptance_report_script.py README.md docs/交接/requirement_mapping.md docs/real_world_uir_dataset.md docs/real_world_knowledge_loop.md docs/demo_workflow.md docs/交接/final_demo_script.md docs/交接/final_handoff_status.md docs/api_usage_examples.md docs/package_spec.md reports/acceptance_report.json reports/acceptance_report.md
git commit -m "docs: hand off five-priority deepening"
```

---

### Task 14: 重新运行全部真实评测并处理指标缺口

**Files:**
- Modify: relevant schemas/templates/gold only when report evidence identifies a real gap
- Regenerate: `reports/*.json`
- Regenerate: `reports/*.md`

- [ ] **Step 1: 启动全新隔离后端**

Run:

```powershell
$env:DATABASE_URL='sqlite:///./reports/next_phase_final_eval.db'
$env:STORAGE_ROOT='reports/next_phase_final_storage'
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

- [ ] **Step 2: 运行主链路与映射评测**

Run:

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_procurement_doc.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_doc.py --base-url http://127.0.0.1:8000 --timeout 60
```

- [ ] **Step 3: 运行内容、知识和下游评测**

Run:

```powershell
backend\.venv\Scripts\python.exe scripts\eval_content_strategy_comparison.py
backend\.venv\Scripts\python.exe scripts\eval_summary_faithfulness.py
backend\.venv\Scripts\python.exe scripts\eval_content_tag_quality.py
backend\.venv\Scripts\python.exe scripts\eval_review_knowledge_growth.py
backend\.venv\Scripts\python.exe scripts\verify_downstream_contract.py --packages-root reports\real_world_packages --out reports\downstream_contract_eval_report.json --markdown reports\downstream_contract_eval_report.md
```

- [ ] **Step 4: 对照真实报告修复可证明的缺口**

只处理以下有 source evidence 的问题：

- candidate extraction 未看到明确字段：增加窄范围提取。
- 明确标签缺 alias：增加精确 alias。
- 明确格式未被解析：增加有边界的 regex/transform。
- Schema 对全部 subtype 过强：仅对有事实依据的字段改为 conditional/optional，并记录理由。

每个修复先增加一个失败测试，再改实现。来源不存在或语义含糊的字段保持
review-required，不硬凑 strict pass。

- [ ] **Step 5: 重新生成所有受影响报告**

Expected acceptance:

```text
procurement strict = 5/5
general strict >= 2/3
meeting strict >= 2/3
policy strict >= 3/5
mapping recall >= 0.65
badcase violations = 0
package verification = all dataset documents
LLM auto accepted = 0
old snapshot unchanged = true
rejected candidate activated = 0
```

第二阶段阈值尽力推进；若真实语义不支持，报告与 handoff 明确记录，不降低门槛。

- [ ] **Step 6: 提交最终真实证据**

```powershell
git add examples/production_like examples/real_world reports docs/交接/requirement_mapping.md docs/real_world_uir_dataset.md docs/real_world_knowledge_loop.md docs/demo_workflow.md docs/交接/final_demo_script.md docs/交接/final_handoff_status.md docs/api_usage_examples.md docs/package_spec.md
git commit -m "test: regenerate five-priority evaluation evidence"
```

---

### Task 15: 完整质量门禁与交付审计

**Files:**
- Verify all changed files

- [ ] **Step 1: 运行新增专项测试**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_real_world_validation_gap_analysis.py backend/tests/test_non_procurement_schema_templates.py backend/tests/test_general_doc_mapping_rules.py backend/tests/test_meeting_doc_mapping_rules.py backend/tests/test_policy_doc_mapping_rules.py backend/tests/test_real_world_non_procurement_validation.py backend/tests/test_real_world_dataset_inventory.py backend/tests/test_content_strategy_comparison.py backend/tests/test_summary_faithfulness_eval.py backend/tests/test_content_tag_quality_eval.py backend/tests/test_review_knowledge_growth.py backend/tests/test_downstream_exports.py backend/tests/test_downstream_contract.py -q
```

Expected: all PASS.

- [ ] **Step 2: 运行后端完整测试和 Ruff**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest -q
backend\.venv\Scripts\python.exe -m ruff check .
```

Expected: zero failures; Ruff clean.

- [ ] **Step 3: 运行前端测试与生产构建**

Run:

```powershell
cd frontend
npm.cmd test -- --run
npm.cmd run build
```

Expected: tests and build succeed.

- [ ] **Step 4: 运行统一验证**

Run:

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

Expected: exit 0; pytest、Ruff、frontend build 和 OpenAPI 均通过。

- [ ] **Step 5: 逐项审计 Definition of Done**

读取八组新报告、真实映射、采购、LLM fallback 和 acceptance JSON，逐项核对指导文档
17 条 Definition of Done。任何未满足项必须在最终回复和
`docs/交接/final_handoff_status.md` 中列为未完成，不用“基本完成”掩盖。

- [ ] **Step 6: 检查工作树与提交范围**

Run:

```powershell
git status --short
git diff --check
git log --oneline main..HEAD
```

Expected: 无意外文件、无空白错误；用户提供的未跟踪指导文档保持原样，除非用户明确
要求纳入版本控制。
