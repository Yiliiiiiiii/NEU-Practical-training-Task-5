# SchemaPack Agent 课题 5 Phase 0 验收报告

> 基于当前可读取证据，已通过检查：package_verification。尚未形成完整通过证据：downstream_smoke=missing、frontend_build=not_run、production_like_eval=missing、pytest=not_run、real_world_eval=partial。本报告不会把缺失、未运行或部分通过的检查表述为已完成。

- 生成时间（UTC）：`2026-06-29T14:31:44.714926+00:00`
- 核心链路：`UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP`

## 1. 项目定位

SchemaPack Agent 面向已经进入 UIR 的文档内容，提供受 Schema 和 Mapping
约束的确定性转换、校验、成果包生成与人审闭环。验收对象是可复现的工程证据，
而不是对缺失检查的推测。

## 2. 课题 5 要求对应关系

课题 5 要求覆盖 UIR 治理输入、Schema 驱动转换、映射模板、人审知识增长、
结构化与可读输出、成果包验证及下游消费。对应关系以
`docs/requirement_mapping.md` 为主证据，其读取状态为
`present`。

## 3. 当前实现能力总览

| 检查 | 状态 | 证据结论 | 建议复现命令 |
| --- | --- | --- | --- |
| pytest | not_run | the report generator does not execute the backend test suite | `cd backend; python -m pytest -q` |
| frontend_build | not_run | the report generator does not execute the frontend build | `cd frontend; npm run build` |
| production_like_eval | missing | report file not found | `python scripts/eval_production_like.py` |
| real_world_eval | partial | real-world report contains incomplete or failed recorded stages | `python scripts/eval_real_world_uir.py` |
| package_verification | passed | real-world report records package verification for every case | `python scripts/eval_production_like.py` |
| downstream_smoke | missing | downstream smoke summary is not available | `python scripts/eval_production_like.py` |

`not_run`、`missing`、`partial` 和 `error` 均不等同于通过。

## 4. 核心链路说明

`UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP`

链路从受治理的 UIR 开始，经 Schema 选择、字段映射、转换与规范模型构建，
输出 Markdown/JSON/JSONL 等内容并完成校验、清单与 ZIP 封装。

## 5. API 与前端能力说明

当前交接文档记录了文档导入、任务创建与执行、报告读取、人审与知识包操作、
ZIP 下载，以及 React/Vite 工作台。本文只记录文档证据状态
`present`；前端构建仍以独立命令为准。

## 6. 生产类评测结果

- 状态：`missing`
- 原因：report file not found
- 证据：`reports/production_like_eval_report.json`

```json
{}
```

## 7. 真实 UIR 评测结果

- 端到端评测状态：`partial`
- 原因：real-world report contains incomplete or failed recorded stages
- 抽取证据状态：`present`
- UIR 校验证据状态：`present`

```json
{
  "evaluation": {
    "by_doc_type": {
      "general_doc": 3,
      "meeting_doc": 3,
      "policy_doc": 5,
      "procurement_doc": 5
    },
    "dataset_size": 16,
    "high_risk_mapping_count": 0,
    "import_pass_count": 16,
    "mapping_review_required_count": 69,
    "package_verify_pass_count": 16,
    "task_execute_pass_count": 16,
    "typical_failure_cases": [
      {
        "doc_id": "real_general_001_notary_service_guide",
        "doc_type": "general_doc",
        "error": "",
        "stage": "validation"
      },
      {
        "doc_id": "real_general_002_biomed_project_guide",
        "doc_type": "general_doc",
        "error": "",
        "stage": "validation"
      },
      {
        "doc_id": "real_general_003_textile_application_flow",
        "doc_type": "general_doc",
        "error": "",
        "stage": "validation"
      }
    ],
    "typical_success_cases": [
      "real_procurement_001_broadcast_security_supervision",
      "real_procurement_002_special_equipment_bid",
      "real_procurement_003_radiation_monitoring_award"
    ],
    "validation_failed_cases": [
      "real_general_001_notary_service_guide",
      "real_general_002_biomed_project_guide",
      "real_general_003_textile_application_flow",
      "real_meeting_001_changning_executive_minutes",
      "real_meeting_002_shaxian_executive_minutes",
      "real_meeting_003_miluo_executive_minutes",
      "real_policy_001_training_platform_rules",
      "real_policy_002_equipment_renewal",
      "real_policy_003_science_education_guide",
      "real_policy_004_student_loan_relief",
      "real_policy_005_ai_industry_guide"
    ]
  },
  "extraction": {
    "by_format": {
      "html": 13,
      "pdf": 3
    },
    "collection_totals": {
      "downloaded": 16,
      "failed": 0,
      "skipped": 0
    },
    "totals": {
      "extracted": 16,
      "rejected": 0,
      "skipped": 0,
      "sources": 16
    }
  },
  "validation": {
    "totals": {
      "empty_or_mojibake": 0,
      "failed": 0,
      "missing_fields": 0,
      "mojibake": 0,
      "passed": 16,
      "sensitive": 0,
      "total": 16
    }
  }
}
```

## 8. 标准成果包结构

`docs/package_spec.md` 的读取状态为
`present`。标准成果包包含内容 JSON、
Markdown、chunks JSONL、映射/转换/校验/内容组织报告、canonical、metadata、
manifest 与 verifier report，并通过清单中的大小和 SHA-256 信息支持复现核验。

## 9. 下游消费验证

- 成果包验证：`passed` —
  real-world report records package verification for every case
- 下游 smoke：`missing` —
  downstream smoke summary is not available

```json
{
  "downstream_smoke": {},
  "package_verification": {
    "dataset_size": 16,
    "package_verify_pass_count": 16
  }
}
```

## 10. badcase 与人审知识闭环

生产类评测以 gold case 与 badcase 通过率作为回归证据。低置信度、歧义或风险
映射进入人审；经接受的候选先形成 draft knowledge pack，仅 active pack
影响新任务。缺少生产类评测报告时，不宣称该闭环本轮已通过。

## 11. LLM fallback 安全姿态

LLM fallback is optional, disabled by default, and every suggestion is review-required; it cannot autonomously activate production rules. 调用受超时、重试和单任务建议数量约束；
非严格模式失败以警告记录，并要求凭据脱敏。LLM 建议不能绕过 badcase 与人审。

## 12. 项目边界与未实现事项

- **input**：UIR is the governed input to the core conversion pipeline.
- **ocr**：No OCR or scanned-document recognition is implemented.
- **rag**：No full RAG or vector-database implementation is included.
- **model_training**：No model training is implemented.
- **llm_fallback**：LLM fallback is optional, disabled by default, and every suggestion is review-required; it cannot autonomously activate production rules.

## 13. 复现命令

- `pytest`：`cd backend; python -m pytest -q`
- `frontend_build`：`cd frontend; npm run build`
- `production_like_eval`：`python scripts/eval_production_like.py`
- `real_world_eval`：`python scripts/eval_real_world_uir.py`
- `package_verification`：`python scripts/eval_production_like.py`
- `downstream_smoke`：`python scripts/eval_production_like.py`

生成本报告：

`python scripts/build_acceptance_report.py`

## 14. 当前结论

基于当前可读取证据，已通过检查：package_verification。尚未形成完整通过证据：downstream_smoke=missing、frontend_build=not_run、production_like_eval=missing、pytest=not_run、real_world_eval=partial。本报告不会把缺失、未运行或部分通过的检查表述为已完成。
