"""Build the evidence-based phase 0 acceptance report for topic 5."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PRODUCTION_REPORT = "reports/production_like_eval_report.json"
REAL_WORLD_REPORT = "reports/real_world_eval_report.json"
VALIDATION_REPORT = "examples/real_world/reports/validation_report.json"
EXTRACTION_REPORT = "examples/real_world/reports/extraction_report.json"
KNOWLEDGE_LOOP_REPORT = "reports/real_world_knowledge_loop_report.json"
CHUNK_RETRIEVAL_REPORT = "reports/chunk_retrieval_eval_report.json"
LLM_FALLBACK_REPORT = "reports/llm_fallback_eval_report.json"

COMMANDS = {
    "pytest": "cd backend; python -m pytest -q",
    "frontend_build": "cd frontend; npm run build",
    "production_like_eval": "python scripts/eval_production_like.py",
    "real_world_eval": "python scripts/eval_real_world_uir.py",
    "package_verification": "python scripts/eval_production_like.py",
    "downstream_smoke": "python scripts/eval_production_like.py",
    "knowledge_loop": "python scripts/eval_real_world_knowledge_loop.py",
    "chunk_retrieval": "python scripts/eval_chunk_retrieval.py",
    "llm_fallback": "python scripts/eval_llm_fallback_modes.py",
}

PIPELINE = (
    "UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> "
    "Content Organization -> Validate -> Manifest -> ZIP -> Package Verification"
)


def read_json_report(root: Path, relative_path: str, command: str) -> dict[str, Any]:
    """Read an optional JSON report into a structured evidence record."""
    root = Path(root).resolve()
    path = (root / relative_path).resolve()
    base = {
        "report_path": relative_path,
        "recommended_command": command,
    }
    try:
        path.relative_to(root)
    except ValueError:
        return {
            **base,
            "status": "error",
            "reason": "report path escapes repository root",
            "summary": {},
        }
    if not path.is_file():
        return {
            **base,
            "status": "missing",
            "reason": "report file not found",
            "summary": {},
        }

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return {
            **base,
            "status": "error",
            "reason": f"report could not be read: {exc}",
            "summary": {},
        }
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return {
            **base,
            "status": "error",
            "reason": f"invalid JSON: {exc}",
            "summary": {},
        }

    if not isinstance(data, dict):
        return {
            **base,
            "status": "error",
            "reason": "invalid JSON: report root must be an object",
            "summary": {},
        }
    return {
        **base,
        "status": "present",
        "reason": "report loaded",
        "summary": data,
    }


def _document_evidence(root: Path, relative_path: str) -> dict[str, Any]:
    path = root / relative_path
    if not path.is_file():
        return {
            "status": "missing",
            "reason": "document file not found",
            "report_path": relative_path,
            "summary": {},
        }
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return {
            "status": "error",
            "reason": f"document could not be read: {exc}",
            "report_path": relative_path,
            "summary": {},
        }
    first_heading = next(
        (
            line.removeprefix("# ").strip()
            for line in text.splitlines()
            if line.startswith("# ")
        ),
        "",
    )
    return {
        "status": "present",
        "reason": "document loaded",
        "report_path": relative_path,
        "summary": {
            "line_count": len(text.splitlines()),
            "title": first_heading,
        },
    }


def _copy_evidence(
    evidence: dict[str, Any],
    *,
    summary: dict[str, Any],
    status: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    result = {key: value for key, value in evidence.items() if key != "summary"}
    result["status"] = status or evidence["status"]
    result["reason"] = reason or evidence["reason"]
    result["summary"] = summary
    return result


def _production_check(evidence: dict[str, Any]) -> dict[str, Any]:
    if evidence["status"] != "present":
        return evidence
    data = evidence["summary"]
    summary = {
        "evaluation": data.get("summary", {}),
        "phase_a": data.get("phase_a", {}),
        "phase_b": data.get("phase_b", {}),
        "downstream_smoke": data.get("downstream_smoke_summary", {}),
        "remaining_issues": data.get("remaining_issues", []),
    }
    phase_b = data.get("phase_b")
    if not isinstance(phase_b, dict):
        return _copy_evidence(
            evidence,
            summary=summary,
            status="partial",
            reason="report is present but phase_b evidence is missing",
        )
    rates = (
        phase_b.get("gold_case_pass_rate"),
        phase_b.get("badcase_pass_rate"),
    )
    if rates == (1.0, 1.0):
        return _copy_evidence(
            evidence,
            summary=summary,
            status="passed",
            reason="gold and badcase pass rates are 1.0",
        )
    return _copy_evidence(
        evidence,
        summary=summary,
        status="partial",
        reason="report is present but does not record full gold and badcase passes",
    )


def _real_world_check(evidence: dict[str, Any]) -> dict[str, Any]:
    if evidence["status"] != "present":
        return evidence
    data = evidence["summary"]
    summary = {
        key: data.get(key)
        for key in (
            "dataset_size",
            "import_pass_count",
            "task_execute_pass_count",
            "package_verify_pass_count",
            "mapping_review_required_count",
            "high_risk_mapping_count",
            "by_doc_type",
            "typical_success_cases",
            "typical_failure_cases",
            "validation_failed_cases",
        )
        if key in data
    }
    dataset_size = data.get("dataset_size")
    stage_counts = (
        data.get("import_pass_count"),
        data.get("task_execute_pass_count"),
        data.get("package_verify_pass_count"),
    )
    complete = (
        isinstance(dataset_size, int)
        and dataset_size > 0
        and all(count == dataset_size for count in stage_counts)
    )
    if complete:
        return _copy_evidence(
            evidence,
            summary=summary,
            status="passed",
            reason=(
                "all reported real-world cases passed import, task execution, "
                "and package verification; validation gaps are recorded separately"
            ),
        )
    return _copy_evidence(
        evidence,
        summary=summary,
        status="partial",
        reason="real-world report contains incomplete or failed recorded stages",
    )


def _derived_check(
    *,
    status: str,
    reason: str,
    report_path: str,
    command: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "report_path": report_path,
        "recommended_command": command,
        "summary": summary,
    }


def _handoff_verification_check(
    root: Path,
    handoff: dict[str, Any],
    *,
    command: str,
    markers: tuple[str, ...],
    passed_reason: str,
    missing_reason: str,
) -> dict[str, Any]:
    report_path = handoff["report_path"]
    summary = {"documented_command": handoff["status"] == "present"}
    if handoff["status"] != "present":
        return _derived_check(
            status=handoff["status"],
            reason=handoff["reason"],
            report_path=report_path,
            command=command,
            summary=summary,
        )
    text = (root / report_path).read_text(encoding="utf-8")
    missing_markers = [marker for marker in markers if marker not in text]
    summary["markers_present"] = not missing_markers
    summary["missing_markers"] = missing_markers
    return _derived_check(
        status="passed" if not missing_markers else "not_run",
        reason=passed_reason if not missing_markers else missing_reason,
        report_path=report_path,
        command=command,
        summary=summary,
    )


def _package_check(
    production: dict[str, Any], real_world: dict[str, Any]
) -> dict[str, Any]:
    real_summary = real_world.get("summary", {})
    dataset_size = real_summary.get("dataset_size")
    passed_count = real_summary.get("package_verify_pass_count")
    summary = {
        "dataset_size": dataset_size,
        "package_verify_pass_count": passed_count,
    }
    if (
        isinstance(dataset_size, int)
        and dataset_size > 0
        and passed_count == dataset_size
    ):
        return _derived_check(
            status="passed",
            reason="real-world report records package verification for every case",
            report_path=REAL_WORLD_REPORT,
            command=COMMANDS["package_verification"],
            summary=summary,
        )
    if production["status"] in {"missing", "error"} and real_world["status"] in {
        "missing",
        "error",
    }:
        return _derived_check(
            status="missing",
            reason="no readable evaluation report contains package verification evidence",
            report_path=PRODUCTION_REPORT,
            command=COMMANDS["package_verification"],
            summary=summary,
        )
    return _derived_check(
        status="partial",
        reason="package verification evidence is incomplete",
        report_path=REAL_WORLD_REPORT,
        command=COMMANDS["package_verification"],
        summary=summary,
    )


def _downstream_check(production: dict[str, Any]) -> dict[str, Any]:
    smoke = production.get("summary", {}).get("downstream_smoke", {})
    if isinstance(smoke, dict) and smoke:
        failed_count = smoke.get("failed_count")
        status = "passed" if failed_count == 0 else "failed"
        reason = (
            "production-like report records zero downstream smoke failures"
            if status == "passed"
            else "production-like report records downstream smoke failures"
        )
        return _derived_check(
            status=status,
            reason=reason,
            report_path=PRODUCTION_REPORT,
            command=COMMANDS["downstream_smoke"],
            summary=smoke,
        )
    source_status = production["status"]
    return _derived_check(
        status="missing" if source_status == "missing" else "partial",
        reason="downstream smoke summary is not available",
        report_path=PRODUCTION_REPORT,
        command=COMMANDS["downstream_smoke"],
        summary={},
    )


def _knowledge_loop_check(evidence: dict[str, Any]) -> dict[str, Any]:
    if evidence["status"] != "present":
        return _derived_check(
            status=evidence["status"],
            reason=evidence["reason"],
            report_path=evidence["report_path"],
            command=evidence["recommended_command"],
            summary=evidence["summary"],
        )
    summary = evidence["summary"]
    passed = (
        summary.get("badcase_violation_count") == 0
        and summary.get("old_snapshot_unchanged") is True
    )
    return _derived_check(
        status="passed" if passed else "partial",
        reason=(
            "knowledge loop preserved old snapshots and avoided badcase violations"
            if passed
            else "knowledge loop report is present but safety metrics are incomplete"
        ),
        report_path=evidence["report_path"],
        command=evidence["recommended_command"],
        summary={
            "approved_candidates": summary.get("approved_candidates"),
            "rejected_candidates": summary.get("rejected_candidates"),
            "badcase_violation_count": summary.get("badcase_violation_count"),
            "old_snapshot_unchanged": summary.get("old_snapshot_unchanged"),
            "before": summary.get("before"),
            "after": summary.get("after"),
        },
    )


def _chunk_retrieval_check(evidence: dict[str, Any]) -> dict[str, Any]:
    if evidence["status"] != "present":
        return _derived_check(
            status=evidence["status"],
            reason=evidence["reason"],
            report_path=evidence["report_path"],
            command=evidence["recommended_command"],
            summary=evidence["summary"],
        )
    summary = evidence["summary"]
    strategies = summary.get("strategies", {})
    recall_values = [
        metrics.get("recall@5")
        for metrics in strategies.values()
        if isinstance(metrics, dict)
    ]
    passed = summary.get("status") == "completed" and all(
        isinstance(value, int | float) and value >= 0.75 for value in recall_values
    )
    return _derived_check(
        status="passed" if passed else "partial",
        reason=(
            "chunk retrieval report meets Recall@5 threshold for recorded strategies"
            if passed
            else "chunk retrieval report is present but at least one strategy is below threshold"
        ),
        report_path=evidence["report_path"],
        command=evidence["recommended_command"],
        summary={
            "status": summary.get("status"),
            "query_count": summary.get("query_count"),
            "strategies": strategies,
        },
    )


def _llm_fallback_check(evidence: dict[str, Any]) -> dict[str, Any]:
    if evidence["status"] != "present":
        return _derived_check(
            status=evidence["status"],
            reason=evidence["reason"],
            report_path=evidence["report_path"],
            command=evidence["recommended_command"],
            summary=evidence["summary"],
        )
    metrics = evidence["summary"].get("metrics", {})
    passed = (
        metrics.get("auto_accepted_count") == 0
        and metrics.get("secret_redaction_passed") is True
    )
    return _derived_check(
        status="passed" if passed else "partial",
        reason=(
            "LLM fallback report confirms review-only suggestions and secret redaction"
            if passed
            else "LLM fallback report is present but safety metrics are incomplete"
        ),
        report_path=evidence["report_path"],
        command=evidence["recommended_command"],
        summary=metrics,
    )


def build_acceptance_report(root: Path) -> dict[str, Any]:
    """Collect available evidence without running evaluations or fabricating passes."""
    root = Path(root)
    production_evidence = read_json_report(
        root,
        PRODUCTION_REPORT,
        COMMANDS["production_like_eval"],
    )
    real_world_evidence = read_json_report(
        root,
        REAL_WORLD_REPORT,
        COMMANDS["real_world_eval"],
    )
    validation_evidence = read_json_report(
        root,
        VALIDATION_REPORT,
        "python scripts/validate_real_world_uir.py",
    )
    extraction_evidence = read_json_report(
        root,
        EXTRACTION_REPORT,
        "python scripts/build_real_world_uir.py",
    )
    knowledge_loop_evidence = read_json_report(
        root,
        KNOWLEDGE_LOOP_REPORT,
        COMMANDS["knowledge_loop"],
    )
    chunk_retrieval_evidence = read_json_report(
        root,
        CHUNK_RETRIEVAL_REPORT,
        COMMANDS["chunk_retrieval"],
    )
    llm_fallback_evidence = read_json_report(
        root,
        LLM_FALLBACK_REPORT,
        COMMANDS["llm_fallback"],
    )

    production = _production_check(production_evidence)
    real_world = _real_world_check(real_world_evidence)
    package = _package_check(production, real_world)
    downstream = _downstream_check(production)
    knowledge_loop = _knowledge_loop_check(knowledge_loop_evidence)
    chunk_retrieval = _chunk_retrieval_check(chunk_retrieval_evidence)
    llm_fallback = _llm_fallback_check(llm_fallback_evidence)
    docs = {
        name: _document_evidence(root, path)
        for name, path in {
            "package_spec": "docs/package_spec.md",
            "requirement_mapping": "docs/交接/requirement_mapping.md",
            "final_handoff_status": "docs/交接/final_handoff_status.md",
        }.items()
    }
    final_handoff = docs["final_handoff_status"]
    checks = {
        "pytest": _handoff_verification_check(
            root,
            final_handoff,
            command=COMMANDS["pytest"],
            markers=(
                "Backend pytest: 567 passed.",
                "Ruff: clean.",
                "OpenAPI export: 63 paths",
            ),
            passed_reason=(
                "final handoff records the backend pytest, ruff, and OpenAPI "
                "verification gate as passed"
            ),
            missing_reason=(
                "final handoff does not yet record the backend verification output"
            ),
        ),
        "frontend_build": _handoff_verification_check(
            root,
            final_handoff,
            command=COMMANDS["frontend_build"],
            markers=("Frontend production build: successful.",),
            passed_reason=(
                "final handoff records the frontend production build as successful"
            ),
            missing_reason=(
                "final handoff does not yet record the frontend verification output"
            ),
        ),
        "production_like_eval": production,
        "real_world_eval": real_world,
        "package_verification": package,
        "downstream_smoke": downstream,
        "knowledge_loop": knowledge_loop,
        "chunk_retrieval": chunk_retrieval,
        "llm_fallback": llm_fallback,
    }

    validation_summary = validation_evidence.get("summary", {})
    extraction_summary = extraction_evidence.get("summary", {})
    evidence = {
        "production_like_eval": production,
        "real_world_eval": real_world,
        "real_world_validation": _copy_evidence(
            validation_evidence,
            summary={"totals": validation_summary.get("totals", {})},
        )
        if validation_evidence["status"] == "present"
        else validation_evidence,
        "real_world_extraction": _copy_evidence(
            extraction_evidence,
            summary={
                "totals": extraction_summary.get("totals", {}),
                "collection_totals": extraction_summary.get("collection_totals", {}),
                "by_format": extraction_summary.get("by_format", {}),
            },
        )
        if extraction_evidence["status"] == "present"
        else extraction_evidence,
        "knowledge_loop": knowledge_loop,
        "chunk_retrieval": chunk_retrieval,
        "llm_fallback": llm_fallback,
        "documents": docs,
    }
    return {
        "project": "SchemaPack Agent",
        "topic": "课题 5：文档内容智能化转换与组织",
        "generated_at": datetime.now(UTC).isoformat(),
        "pipeline": PIPELINE,
        "checks": checks,
        "evidence": evidence,
        "boundaries": {
            "input": "UIR is the governed input to the core conversion pipeline.",
            "ocr": (
                "No OCR or scanned-document recognition is implemented. Optional "
                "offline Docling/Unstructured entry scripts can produce External UIR "
                "from supported local files without changing the production runtime."
            ),
            "rag": "No full RAG or vector-database implementation is included.",
            "model_training": "No model training is implemented.",
            "llm_fallback": (
                "LLM fallback is optional, disabled by default, and every suggestion "
                "is review-required; it cannot autonomously activate production rules."
            ),
        },
    }


def _json_block(value: Any) -> str:
    return (
        "```json\n"
        + json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n```"
    )


def _conclusion(report: dict[str, Any]) -> str:
    checks = report["checks"]
    passed = sorted(
        name for name, check in checks.items() if check["status"] == "passed"
    )
    outstanding = sorted(
        f"{name}={check['status']}"
        for name, check in checks.items()
        if check["status"] != "passed"
    )
    passed_text = "、".join(passed) if passed else "无"
    outstanding_text = "、".join(outstanding) if outstanding else "无"
    return (
        f"基于当前可读取证据，已通过检查：{passed_text}。"
        f"尚未形成完整通过证据：{outstanding_text}。"
        "本报告不会把缺失、未运行或部分通过的检查表述为已完成。"
    )


def render_markdown(report: dict[str, Any]) -> str:
    """Render the acceptance report with the guideline's 14 numbered sections."""
    checks = report["checks"]
    evidence = report["evidence"]
    boundaries = report["boundaries"]
    conclusion = _conclusion(report)
    check_rows = "\n".join(
        f"| {name} | {check['status']} | {check['reason']} | "
        f"`{check['recommended_command']}` |"
        for name, check in checks.items()
    )
    boundary_rows = "\n".join(
        f"- **{name}**：{description}" for name, description in boundaries.items()
    )
    commands = "\n".join(
        f"- `{name}`：`{check['recommended_command']}`"
        for name, check in checks.items()
    )
    markdown = f"""# SchemaPack Agent 课题 5 Phase 0 验收报告

> {conclusion}

- 生成时间（UTC）：`{report["generated_at"]}`
- 核心链路：`{report["pipeline"]}`

## 1. 项目定位

SchemaPack Agent 面向已经进入 UIR 的文档内容，提供受 Schema 和 Mapping
约束的确定性转换、校验、成果包生成与人审闭环。验收对象是可复现的工程证据，
而不是对缺失检查的推测。

## 2. 课题 5 要求对应关系

课题 5 要求覆盖 UIR 治理输入、Schema 驱动转换、映射模板、人审知识增长、
结构化与可读输出、成果包验证及下游消费。对应关系以
`docs/交接/requirement_mapping.md` 为主证据，其读取状态为
`{evidence["documents"]["requirement_mapping"]["status"]}`。

## 3. 当前实现能力总览

| 检查 | 状态 | 证据结论 | 建议复现命令 |
| --- | --- | --- | --- |
{check_rows}

`not_run`、`missing`、`partial` 和 `error` 均不等同于通过。

## 4. 核心链路说明

`{report["pipeline"]}`

链路从受治理的 UIR 开始，经 Schema 选择、字段映射、转换与规范模型构建，
输出 Markdown/JSON/JSONL 等内容并完成校验、清单与 ZIP 封装。

## 5. API 与前端能力说明

当前交接文档记录了文档导入、任务创建与执行、报告读取、人审与知识包操作、
ZIP 下载，以及 React/Vite 工作台。本文只记录文档证据状态
`{evidence["documents"]["final_handoff_status"]["status"]}`；前端构建仍以独立命令为准。

## 6. 生产类评测结果

- 状态：`{checks["production_like_eval"]["status"]}`
- 原因：{checks["production_like_eval"]["reason"]}
- 证据：`{checks["production_like_eval"]["report_path"]}`

{_json_block(checks["production_like_eval"]["summary"])}

## 7. 真实 UIR 评测结果

- 端到端评测状态：`{checks["real_world_eval"]["status"]}`
- 原因：{checks["real_world_eval"]["reason"]}
- 抽取证据状态：`{evidence["real_world_extraction"]["status"]}`
- UIR 校验证据状态：`{evidence["real_world_validation"]["status"]}`

{_json_block({
    "evaluation": checks["real_world_eval"]["summary"],
    "extraction": evidence["real_world_extraction"]["summary"],
    "validation": evidence["real_world_validation"]["summary"],
})}

## 8. 标准成果包结构

`docs/package_spec.md` 的读取状态为
`{evidence["documents"]["package_spec"]["status"]}`。标准成果包包含内容 JSON、
Markdown、chunks JSONL、映射/转换/校验/内容组织报告、canonical、metadata、
manifest 与 verifier report，并通过清单中的大小和 SHA-256 信息支持复现核验。

## 9. 下游消费验证

- 成果包验证：`{checks["package_verification"]["status"]}` —
  {checks["package_verification"]["reason"]}
- 下游 smoke：`{checks["downstream_smoke"]["status"]}` —
  {checks["downstream_smoke"]["reason"]}

{_json_block({
    "package_verification": checks["package_verification"]["summary"],
    "downstream_smoke": checks["downstream_smoke"]["summary"],
})}

## 10. badcase 与人审知识闭环

生产类评测以 gold case 与 badcase 通过率作为回归证据。低置信度、歧义或风险
映射进入人审；经接受的候选先形成 draft knowledge pack，仅 active pack
影响新任务。缺少生产类评测报告时，不宣称该闭环本轮已通过。

## 11. LLM fallback 安全姿态

{boundaries["llm_fallback"]} 调用受超时、重试和单任务建议数量约束；
非严格模式失败以警告记录，并要求凭据脱敏。LLM 建议不能绕过 badcase 与人审。

## 12. 项目边界与未实现事项

{boundary_rows}

## 13. 复现命令

{commands}

生成本报告：

`python scripts/build_acceptance_report.py`

## 14. 当前结论

{conclusion}
"""
    return markdown.strip() + "\n"


def write_reports(root: Path, report: dict[str, Any]) -> list[Path]:
    """Write stable JSON plus identical report/docs Markdown artifacts."""
    root = Path(root)
    json_path = root / "reports" / "acceptance_report.json"
    report_markdown_path = root / "reports" / "acceptance_report.md"
    docs_markdown_path = root / "docs" / "交接" / "acceptance_report.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    docs_markdown_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown = render_markdown(report)
    report_markdown_path.write_text(markdown, encoding="utf-8")
    docs_markdown_path.write_text(markdown, encoding="utf-8")
    return [json_path, report_markdown_path, docs_markdown_path]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the script's parent repository)",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    paths = write_reports(root, build_acceptance_report(root))
    for path in paths:
        print(path.relative_to(root).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
