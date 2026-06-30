# SchemaPack Agent 课题 5 Phase 0 验收报告

> 基于当前可读取证据，已通过检查：chunk_retrieval、downstream_smoke、frontend_build、knowledge_loop、llm_fallback、package_verification、production_like_eval、pytest、real_world_eval。尚未形成完整通过证据：无。本报告不会把缺失、未运行或部分通过的检查表述为已完成。

- 生成时间（UTC）：`2026-06-30T07:53:20.254376+00:00`
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
| pytest | passed | final handoff records the backend pytest, ruff, and OpenAPI verification gate as passed | `cd backend; python -m pytest -q` |
| frontend_build | passed | final handoff records the frontend production build as successful | `cd frontend; npm run build` |
| production_like_eval | passed | gold and badcase pass rates are 1.0 | `python scripts/eval_production_like.py` |
| real_world_eval | passed | all reported real-world cases passed import, task execution, and package verification; validation gaps are recorded separately | `python scripts/eval_real_world_uir.py` |
| package_verification | passed | real-world report records package verification for every case | `python scripts/eval_production_like.py` |
| downstream_smoke | passed | production-like report records zero downstream smoke failures | `python scripts/eval_production_like.py` |
| knowledge_loop | passed | knowledge loop preserved old snapshots and avoided badcase violations | `python scripts/eval_real_world_knowledge_loop.py` |
| chunk_retrieval | passed | chunk retrieval report meets Recall@5 threshold for recorded strategies | `python scripts/eval_chunk_retrieval.py` |
| llm_fallback | passed | LLM fallback report confirms review-only suggestions and secret redaction | `python scripts/eval_llm_fallback_modes.py` |

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

- 状态：`passed`
- 原因：gold and badcase pass rates are 1.0
- 证据：`reports/production_like_eval_report.json`

```json
{
  "downstream_smoke": {
    "failed_count": 0,
    "package_count": 15,
    "passed_count": 15,
    "results": [
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_contract_001_standard\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_contract_001_standard_con001_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_contract_002_party_alias\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_contract_002_party_alias_con002_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_contract_003_amount_transform\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_contract_003_amount_transform_con003_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_contract_004_enum_status\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_contract_004_enum_status_con004_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_general_001_standard\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_general_001_standard_gen001_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_general_002_mixed_metadata\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_general_002_mixed_metadata_gen002_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_general_003_table_like_blocks\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_general_003_table_like_blocks_gen003_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_meeting_001_standard\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_meeting_001_standard_met001_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_meeting_002_attendee_variants\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_meeting_002_attendee_variants_met002_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_meeting_003_missing_required\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_meeting_003_missing_required_met003_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_policy_001_standard\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_policy_001_standard_pol001_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_policy_002_alias_variants\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_policy_002_alias_variants_pol002_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_policy_003_unmapped_required\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_policy_003_unmapped_required_pol003_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_policy_004_low_confidence\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_policy_004_low_confidence_pol004_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_policy_005_regex_case\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_policy_005_regex_case_pol005_b001_1"
      }
    ]
  },
  "evaluation": {
    "auto_mapped_fields": 71,
    "auto_mapping_rate": 0.6228,
    "badcase_pass_rate": 1.0,
    "badcase_violation_count": 0,
    "candidates_approved": 39,
    "candidates_by_type": {
      "alias": 56,
      "exact": 15,
      "fuzzy": 25
    },
    "cases_by_domain": {
      "contract_doc": 4,
      "general_doc": 3,
      "meeting_doc": 3,
      "policy_doc": 5
    },
    "confidence_bucket_accuracy": "not_available",
    "effective_template_pack_resolution_count": 15,
    "failed_mapping_fields": 7,
    "failed_mapping_rate": 0.0614,
    "gold_case_pass_rate": 1.0,
    "knowledge_candidates_generated": 25,
    "mapping_total_fields": 114,
    "package_success_rate": 1.0,
    "packs_activated": 1,
    "packs_created": 1,
    "review_required_fields": 25,
    "review_required_rate": 0.2193,
    "schema_validation_pass_rate": 0.7333,
    "total_cases": 15,
    "unmapped_required_fields": 7
  },
  "phase_a": {
    "auto_mapped_fields": 58,
    "auto_mapping_rate": 0.5088,
    "badcase_pass_rate": 1.0,
    "badcase_violation_count": 0,
    "candidates_approved": 0,
    "candidates_by_type": {
      "alias": 43,
      "exact": 15,
      "fuzzy": 39
    },
    "cases_by_domain": {
      "contract_doc": 4,
      "general_doc": 3,
      "meeting_doc": 3,
      "policy_doc": 5
    },
    "confidence_bucket_accuracy": "not_available",
    "effective_template_pack_resolution_count": 0,
    "failed_mapping_fields": 16,
    "failed_mapping_rate": 0.1404,
    "gold_case_pass_rate": 0.48,
    "knowledge_candidates_generated": 39,
    "mapping_total_fields": 114,
    "package_success_rate": 1.0,
    "packs_activated": 0,
    "packs_created": 0,
    "review_required_fields": 39,
    "review_required_rate": 0.3421,
    "schema_validation_pass_rate": 0.4,
    "total_cases": 15,
    "unmapped_required_fields": 16
  },
  "phase_b": {
    "auto_mapped_fields": 71,
    "auto_mapping_rate": 0.6228,
    "badcase_pass_rate": 1.0,
    "badcase_violation_count": 0,
    "candidates_approved": 39,
    "candidates_by_type": {
      "alias": 56,
      "exact": 15,
      "fuzzy": 25
    },
    "cases_by_domain": {
      "contract_doc": 4,
      "general_doc": 3,
      "meeting_doc": 3,
      "policy_doc": 5
    },
    "confidence_bucket_accuracy": "not_available",
    "effective_template_pack_resolution_count": 15,
    "failed_mapping_fields": 7,
    "failed_mapping_rate": 0.0614,
    "gold_case_pass_rate": 1.0,
    "knowledge_candidates_generated": 25,
    "mapping_total_fields": 114,
    "package_success_rate": 1.0,
    "packs_activated": 1,
    "packs_created": 1,
    "review_required_fields": 25,
    "review_required_rate": 0.2193,
    "schema_validation_pass_rate": 0.7333,
    "total_cases": 15,
    "unmapped_required_fields": 7
  },
  "remaining_issues": [
    "Authentication, authorization, tenancy, audit logging, hosted model operations, and production access controls are not implemented."
  ]
}
```

## 7. 真实 UIR 评测结果

- 端到端评测状态：`passed`
- 原因：all reported real-world cases passed import, task execution, and package verification; validation gaps are recorded separately
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
    "mapping_review_required_count": 65,
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
- 下游 smoke：`passed` —
  production-like report records zero downstream smoke failures

```json
{
  "downstream_smoke": {
    "failed_count": 0,
    "package_count": 15,
    "passed_count": 15,
    "results": [
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_contract_001_standard\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_contract_001_standard_con001_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_contract_002_party_alias\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_contract_002_party_alias_con002_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_contract_003_amount_transform\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_contract_003_amount_transform_con003_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_contract_004_enum_status\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_contract_004_enum_status_con004_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_general_001_standard\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_general_001_standard_gen001_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_general_002_mixed_metadata\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_general_002_mixed_metadata_gen002_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_general_003_table_like_blocks\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_general_003_table_like_blocks_gen003_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_meeting_001_standard\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_meeting_001_standard_met001_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_meeting_002_attendee_variants\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_meeting_002_attendee_variants_met002_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_meeting_003_missing_required\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_meeting_003_missing_required_met003_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_policy_001_standard\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_policy_001_standard_pol001_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_policy_002_alias_variants\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_policy_002_alias_variants_pol002_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_policy_003_unmapped_required\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_policy_003_unmapped_required_pol003_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_policy_004_low_confidence\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_policy_004_low_confidence_pol004_b001_1"
      },
      {
        "errors": [],
        "package": "F:\\p2\\reports\\packages\\phase_b\\packages\\pkg_eval_policy_005_regex_case\\standard_package.zip",
        "passed": true,
        "source_linked": true,
        "top_hit_chunk_id": "chunk_policy_005_regex_case_pol005_b001_1"
      }
    ]
  },
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
- `knowledge_loop`：`python scripts/eval_real_world_knowledge_loop.py`
- `chunk_retrieval`：`python scripts/eval_chunk_retrieval.py`
- `llm_fallback`：`python scripts/eval_llm_fallback_modes.py`

生成本报告：

`python scripts/build_acceptance_report.py`

## 14. 当前结论

基于当前可读取证据，已通过检查：chunk_retrieval、downstream_smoke、frontend_build、knowledge_loop、llm_fallback、package_verification、production_like_eval、pytest、real_world_eval。尚未形成完整通过证据：无。本报告不会把缺失、未运行或部分通过的检查表述为已完成。
