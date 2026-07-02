# Non-procurement Mapping Recall Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible non-procurement gap-analysis and evaluation loop, then improve evidence-backed mapping recall for `general_doc`, `meeting_doc`, and `policy_doc` without weakening badcase safety.

**Architecture:** Reuse the existing API evaluator, mapping pipeline, schemas, templates, and report helpers. Add one offline artifact analyzer and one compatibility evaluator entry point, then make narrow TDD changes to candidate extraction, templates, transforms, and badcases. Keep current core required fields unchanged unless fresh analyzer evidence proves a schema defect.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, JSON/JSONL catalogs, PowerShell, TypeScript/Vite.

---

## File Map

- Create `reports/non_procurement_baseline_report.json`: immutable starting metrics.
- Create `reports/non_procurement_baseline_report.md`: readable baseline and provenance.
- Create `scripts/analyze_non_procurement_gaps.py`: package discovery, evidence joining, gap classification, and report rendering.
- Create `backend/tests/test_analyze_non_procurement_gaps.py`: analyzer contract and classification tests.
- Modify `backend/app/services/candidate_service.py`: heading, title-path, Chinese key/value, headed-list, and paragraph-regex candidates.
- Create `backend/tests/test_candidate_service_non_procurement.py`: focused candidate extraction tests.
- Modify three files under `examples/production_like/mapping_templates/`: low-risk aliases and regexes only.
- Create `backend/tests/test_non_procurement_templates.py`: schema-target and safety checks.
- Modify `backend/app/services/transform_service.py`: date, array, and contact normalization.
- Create `backend/tests/test_non_procurement_transform.py`: field-aware normalization tests.
- Create `backend/tests/test_non_procurement_schema_validation.py`: lock current core requirements and procurement isolation.
- Create `reports/non_procurement_schema_adjustments.md`: explicit record that no requirement is relaxed without evidence.
- Modify `examples/real_world/gold/real_world_badcases.jsonl`: add confusion-pair safety cases with source evidence.
- Create `backend/tests/test_non_procurement_badcases.py`: badcase dataset and mapping enforcement tests.
- Create `scripts/eval_non_procurement_mapping.py`: guide-compatible evaluator CLI and richer report contract.
- Create `backend/tests/test_eval_non_procurement_mapping.py`: report, delta, and Markdown tests.
- Create `docs/non_procurement_mapping_improvement_plan.md`: ranked fixes derived from analyzer output.
- Generate `reports/non_procurement_gap_analysis.json` and `.md`.
- Generate `reports/non_procurement_mapping_eval_report.json` and `.md`.
- Create `reports/non_procurement_acceptance_report.md`: threshold-by-threshold result.
- Update `README.md`, `docs/final_handoff_status.md`, `docs/requirement_mapping.md`, `docs/real_world_uir_dataset.md`, `docs/badcase_analysis.md`, and `docs/developer_guide.md`.

### Task 1: Freeze the Verified Baseline

**Files:**
- Create: `reports/non_procurement_baseline_report.json`
- Create: `reports/non_procurement_baseline_report.md`

- [ ] **Step 1: Re-run the existing baseline verification**

Run:

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

Expected: exit `0`, backend pytest reports no failures, ruff is clean, frontend build succeeds, and OpenAPI export succeeds.

- [ ] **Step 2: Start the API and run the existing non-procurement evaluator**

Run in a hidden background process:

```powershell
$server = Start-Process backend\.venv\Scripts\python.exe `
  -ArgumentList '-m','uvicorn','app.main:app','--app-dir','backend','--host','127.0.0.1','--port','8000' `
  -WindowStyle Hidden -PassThru
```

Poll until ready:

```powershell
for ($attempt = 0; $attempt -lt 30; $attempt++) {
  try {
    Invoke-WebRequest http://127.0.0.1:8000/docs -UseBasicParsing | Out-Null
    break
  } catch {
    Start-Sleep -Seconds 1
  }
}
if ($attempt -eq 30) { throw 'API did not become ready' }
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_doc.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60
```

Expected: exit `0` and `reports/non_procurement_doc_eval_report.json` contains 20 documents.

- [ ] **Step 3: Add the baseline JSON from the fresh evaluator**

Create exactly this stable artifact, using the fresh report values if any metric differs:

```json
{
  "dataset_size": 30,
  "non_procurement_dataset_size": 20,
  "strict_pass_count": 4,
  "required_missing_count": 18,
  "review_required_count": 145,
  "average_recall": 0.3494047619047619,
  "badcase_violation_count": 0,
  "package_verify_pass_count": 20,
  "source_report": "reports/non_procurement_doc_eval_report.json"
}
```

- [ ] **Step 4: Add the readable baseline**

```markdown
# Non-procurement Mapping Baseline

## Metrics

| Dataset | Documents | Strict pass | Average recall | Review required | Required missing | Badcase violations | Package valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Full real-world | 30 | — | — | — | — | — | — |
| Non-procurement | 20 | 4 | 0.3494 | 145 | 18 | 0 | 20 |

## Provenance

- Source: `reports/non_procurement_doc_eval_report.json`
- Command: `backend\.venv\Scripts\python.exe scripts\eval_non_procurement_doc.py --base-url http://127.0.0.1:8000 --timeout 60`
- The baseline was generated by the API-backed evaluator and was not edited to improve metrics.
```

- [ ] **Step 5: Validate and commit the baseline**

Run:

```powershell
Get-Content -Raw -Encoding UTF8 reports\non_procurement_baseline_report.json | ConvertFrom-Json | Out-Null
git add reports/non_procurement_baseline_report.json reports/non_procurement_baseline_report.md
git commit -m "test: freeze non-procurement mapping baseline"
```

Expected: JSON parses and the commit contains only the two baseline files.

### Task 2: Add the Non-procurement Gap Analyzer

**Files:**
- Create: `backend/tests/test_analyze_non_procurement_gaps.py`
- Create: `scripts/analyze_non_procurement_gaps.py`

- [ ] **Step 1: Write failing discovery and classification tests**

```python
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analyze_non_procurement_gaps.py"


def load_module():
    spec = importlib.util.spec_from_file_location("analyze_non_procurement_gaps", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_discover_packages_recurses_and_requires_core_artifacts(tmp_path: Path):
    module = load_module()
    package = tmp_path / "nested" / "doc-a"
    for name in (
        "metadata.json",
        "mapping_report.json",
        "validation_report.json",
        "content.json",
        "canonical.json",
    ):
        write_json(package / name, {})
    write_json(tmp_path / "partial" / "metadata.json", {})

    assert module.discover_packages(tmp_path) == [package]


def test_analyze_classifies_missing_candidate_and_badcase_sensitive(tmp_path: Path):
    module = load_module()
    package = tmp_path / "doc-a"
    write_json(package / "metadata.json", {"doc_id": "doc-a", "schema_id": "policy_doc"})
    write_json(
        package / "mapping_report.json",
        {
            "summary": {"review_required_count": 1},
            "mappings": [],
            "review_required_items": [{
                "target_field_id": "effective_date",
                "source_field": {"source_name": "发布日期", "value_sample": "2026-07-01"},
                "source_blocks": ["b1"],
                "review_required_reason": "badcase_blocked",
                "risk_flags": ["badcase_blocked"],
            }, {
                "target_field_id": "policy_measures",
                "source_field": {"source_name": "政策措施", "value_sample": "措施一；措施二"},
                "source_blocks": ["b2"],
                "review_required_reason": "target expects array",
                "risk_flags": ["type_mismatch"],
            }],
            "unmapped": [{"target_field_id": "issuer", "required": True}],
        },
    )
    write_json(
        package / "validation_report.json",
        {
            "passed": False,
            "issues": [{"code": "required_field_missing", "field_id": "issuer"}],
        },
    )
    write_json(package / "content.json", {"blocks": [{"block_id": "b1", "text": "发布日期：2026-07-01"}]})
    write_json(package / "canonical.json", {"data": {}})
    gold = [{"doc_id": "doc-a", "doc_type": "policy_doc", "expected_mappings": [{"target_field": "issuer"}]}]
    badcases = [{
        "doc_id": "doc-a",
        "forbidden_auto_mapping": {"source_name": "发布日期", "target_field": "effective_date"},
    }]

    report = module.analyze_packages([package], gold, badcases, top_n=30)

    assert report["summary"]["documents_total"] == 1
    assert report["candidate_extraction_gaps"][0]["target_field"] == "issuer"
    assert report["badcase_sensitive_items"][0]["target_field"] == "effective_date"
    assert report["transform_gaps"][0]["target_field"] == "policy_measures"
    assert set(report) >= {
        "top_missing_required_fields",
        "top_review_required_fields",
        "alias_gaps",
        "regex_gaps",
        "schema_gaps",
        "transform_gaps",
        "recommended_plan",
    }
```

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_analyze_non_procurement_gaps.py -q
cd ..
```

Expected: FAIL because `scripts/analyze_non_procurement_gaps.py` does not exist.

- [ ] **Step 3: Implement package discovery and report construction**

Create the script with these public interfaces and constants:

```python
"""Analyze non-procurement mapping gaps from generated package artifacts."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from eval_support import load_jsonl, safe_ratio, write_json, write_markdown

ROOT = Path(__file__).resolve().parents[1]
NON_PROCUREMENT_DOC_TYPES = {"general_doc", "meeting_doc", "policy_doc"}
CORE_ARTIFACTS = {
    "metadata.json",
    "mapping_report.json",
    "validation_report.json",
    "content.json",
    "canonical.json",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return value


def discover_packages(packages_root: Path) -> list[Path]:
    if not packages_root.is_dir():
        raise ValueError(f"Package root not found: {packages_root}")
    packages = []
    for metadata in packages_root.rglob("metadata.json"):
        package = metadata.parent
        if all((package / name).is_file() for name in CORE_ARTIFACTS):
            packages.append(package)
    return sorted(set(packages))


def source_name(item: dict[str, Any]) -> str:
    source = item.get("source_field", {})
    return str(source.get("source_name", "")) if isinstance(source, dict) else ""


def target_field(item: dict[str, Any]) -> str:
    return str(item.get("target_field_id") or item.get("target_field") or "")


def gap_item(
    *,
    doc_type: str,
    doc_id: str,
    target: str,
    gap_type: str,
    item: dict[str, Any] | None,
    action: str,
) -> dict[str, Any]:
    item = item or {}
    source = item.get("source_field", {})
    source = source if isinstance(source, dict) else {}
    blocks = item.get("source_blocks", source.get("source_blocks", []))
    return {
        "doc_type": doc_type,
        "doc_id": doc_id,
        "target_field": target,
        "gap_type": gap_type,
        "count": 1,
        "candidate_source_names": [source_name(item)] if source_name(item) else [],
        "candidate_value_samples": [source.get("value_sample")] if source.get("value_sample") else [],
        "source_block_ids": blocks if isinstance(blocks, list) else [],
        "review_required_reason": str(item.get("review_required_reason") or ""),
        "recommended_action": action,
    }


def analyze_packages(
    packages: list[Path],
    gold_rows: list[dict[str, Any]],
    badcases: list[dict[str, Any]],
    *,
    top_n: int,
) -> dict[str, Any]:
    gold_by_doc = {str(row.get("doc_id")): row for row in gold_rows}
    badcase_pairs = {
        (
            str(row.get("doc_id")),
            str(row.get("forbidden_auto_mapping", {}).get("source_name", "")),
            str(row.get("forbidden_auto_mapping", {}).get("target_field", "")),
        )
        for row in badcases
        if isinstance(row.get("forbidden_auto_mapping"), dict)
    }
    categories = {
        "candidate_extraction_gaps": [],
        "alias_gaps": [],
        "regex_gaps": [],
        "schema_gaps": [],
        "transform_gaps": [],
        "badcase_sensitive_items": [],
    }
    missing = Counter()
    reviews = Counter()
    by_type: dict[str, dict[str, int]] = {
        doc_type: {"documents": 0, "strict_pass_count": 0, "required_missing_count": 0, "review_required_count": 0}
        for doc_type in sorted(NON_PROCUREMENT_DOC_TYPES)
    }
    recall_total = 0.0
    badcase_violations = 0

    for package in packages:
        metadata = load_json(package / "metadata.json")
        mapping = load_json(package / "mapping_report.json")
        validation = load_json(package / "validation_report.json")
        doc_id = str(metadata.get("doc_id") or package.name)
        doc_type = str(metadata.get("doc_type") or metadata.get("schema_id") or mapping.get("schema_id") or "")
        if doc_type not in NON_PROCUREMENT_DOC_TYPES:
            continue
        by_type[doc_type]["documents"] += 1
        if validation.get("passed") is True:
            by_type[doc_type]["strict_pass_count"] += 1
        review_items = mapping.get("review_required_items", [])
        review_items = review_items if isinstance(review_items, list) else []
        by_type[doc_type]["review_required_count"] += len(review_items)
        for item in review_items:
            if not isinstance(item, dict):
                continue
            target = target_field(item)
            reviews[(doc_type, target)] += 1
            pair = (doc_id, source_name(item), target)
            flags = item.get("risk_flags", [])
            reason = str(item.get("review_required_reason") or "").lower()
            if pair in badcase_pairs or "badcase_blocked" in flags:
                categories["badcase_sensitive_items"].append(
                    gap_item(doc_type=doc_type, doc_id=doc_id, target=target, gap_type="badcase_sensitive", item=item, action="keep_review_required")
                )
            elif "type_mismatch" in flags or "expects array" in reason or "transform" in reason:
                categories["transform_gaps"].append(
                    gap_item(doc_type=doc_type, doc_id=doc_id, target=target, gap_type="transform_type_error", item=item, action="enhance_transform")
                )
            elif item.get("method") == "regex":
                categories["regex_gaps"].append(
                    gap_item(doc_type=doc_type, doc_id=doc_id, target=target, gap_type="regex_missing", item=item, action="add_regex")
                )
            else:
                categories["alias_gaps"].append(
                    gap_item(doc_type=doc_type, doc_id=doc_id, target=target, gap_type="alias_missing", item=item, action="add_alias")
                )
        unmapped = mapping.get("unmapped", [])
        unmapped = unmapped if isinstance(unmapped, list) else []
        expected = gold_by_doc.get(doc_id, {}).get("expected_mappings", [])
        expected_targets = {
            str(row.get("target_field") or row.get("target_field_id"))
            for row in expected
            if isinstance(row, dict)
        }
        for item in unmapped:
            if not isinstance(item, dict) or not item.get("required"):
                continue
            target = target_field(item)
            missing[(doc_type, target)] += 1
            by_type[doc_type]["required_missing_count"] += 1
            category = "candidate_extraction_gaps" if target in expected_targets else "schema_gaps"
            categories[category].append(
                gap_item(
                    doc_type=doc_type,
                    doc_id=doc_id,
                    target=target,
                    gap_type="candidate_not_extracted" if category == "candidate_extraction_gaps" else "schema_too_strict",
                    item=item,
                    action="enhance_candidate" if category == "candidate_extraction_gaps" else "review_schema",
                )
            )
        summary = mapping.get("summary", {})
        summary = summary if isinstance(summary, dict) else {}
        recall_total += float(summary.get("mapping_recall", 0.0) or 0.0)
        badcase_violations += int(summary.get("badcase_violation_count", 0) or 0)

    documents_total = sum(item["documents"] for item in by_type.values())
    strict_pass_count = sum(item["strict_pass_count"] for item in by_type.values())
    required_missing_count = sum(item["required_missing_count"] for item in by_type.values())
    review_required_count = sum(item["review_required_count"] for item in by_type.values())
    report = {
        "summary": {
            "documents_total": documents_total,
            "overall": {
                "strict_pass_count": strict_pass_count,
                "review_required_count": review_required_count,
                "required_missing_count": required_missing_count,
                "average_recall": safe_ratio(recall_total, documents_total),
                "badcase_violation_count": badcase_violations,
            },
            "by_doc_type": by_type,
        },
        "top_missing_required_fields": [
            {"doc_type": key[0], "target_field": key[1], "count": count}
            for key, count in missing.most_common(top_n)
        ],
        "top_review_required_fields": [
            {"doc_type": key[0], "target_field": key[1], "count": count}
            for key, count in reviews.most_common(top_n)
        ],
        **categories,
        "recommended_plan": [
            {"priority": index, **item}
            for index, item in enumerate(
                sorted(
                    categories["alias_gaps"] + categories["regex_gaps"] + categories["candidate_extraction_gaps"],
                    key=lambda row: (row["gap_type"], row["doc_type"], row["target_field"], row["doc_id"]),
                )[:top_n],
                start=1,
            )
        ],
    }
    return report
```

Add this Markdown renderer and `main()`:

```python
def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]["overall"]
    sections = (
        ("Candidate Extraction Gaps", "candidate_extraction_gaps"),
        ("Alias Gaps", "alias_gaps"),
        ("Regex Rule Gaps", "regex_gaps"),
        ("Schema Required-field Gaps", "schema_gaps"),
        ("Transform / Type Normalization Gaps", "transform_gaps"),
        ("Badcase-sensitive Items", "badcase_sensitive_items"),
        ("Recommended Fix Plan", "recommended_plan"),
    )
    lines = [
        "# Non-procurement Mapping Gap Analysis",
        "",
        "## Summary",
        "",
        f"- Documents: {report['summary']['documents_total']}",
        f"- Strict pass: {summary['strict_pass_count']}",
        f"- Average recall: {summary['average_recall']:.3f}",
        f"- Review required: {summary['review_required_count']}",
        f"- Required missing: {summary['required_missing_count']}",
        f"- Badcase violations: {summary['badcase_violation_count']}",
        "",
        "## By Document Type",
        "",
        "| Type | Documents | Strict pass | Required missing | Review required |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for doc_type, metrics in report["summary"]["by_doc_type"].items():
        lines.append(
            f"| {doc_type} | {metrics['documents']} | {metrics['strict_pass_count']} | "
            f"{metrics['required_missing_count']} | {metrics['review_required_count']} |"
        )
    for heading, key in (
        ("Top Missing Required Fields", "top_missing_required_fields"),
        ("Top Review-required Fields", "top_review_required_fields"),
        *sections,
    ):
        lines.extend(["", f"## {heading}", ""])
        rows = report[key]
        if not rows:
            lines.append("- None")
            continue
        for item in rows:
            lines.append(
                f"- {item.get('doc_type', '')}.{item.get('target_field', '')}: "
                f"{item.get('gap_type', 'count')} "
                f"(count={item.get('count', 1)}, action={item.get('recommended_action', '')})"
            )
    lines.extend(["", "## Do-not-auto-accept List", ""])
    if report["badcase_sensitive_items"]:
        for item in report["badcase_sensitive_items"]:
            lines.append(
                f"- {item['doc_id']}: {', '.join(item['candidate_source_names'])} "
                f"-> {item['target_field']}"
            )
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages-root", type=Path, default=ROOT / "reports" / "real_world_packages")
    parser.add_argument("--gold", type=Path, default=ROOT / "examples" / "real_world" / "gold" / "mapping_gold.jsonl")
    parser.add_argument("--badcases", type=Path, default=ROOT / "examples" / "real_world" / "gold" / "real_world_badcases.jsonl")
    parser.add_argument("--doc-types", default="general_doc,meeting_doc,policy_doc")
    parser.add_argument("--out", type=Path, default=ROOT / "reports" / "non_procurement_gap_analysis.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "reports" / "non_procurement_gap_analysis.md")
    parser.add_argument("--top-n", type=int, default=30)
    args = parser.parse_args()
    requested = {value.strip() for value in args.doc_types.split(",") if value.strip()}
    if not requested <= NON_PROCUREMENT_DOC_TYPES:
        raise SystemExit(f"Unsupported document types: {sorted(requested - NON_PROCUREMENT_DOC_TYPES)}")
    try:
        report = analyze_packages(
            discover_packages(args.packages_root),
            load_jsonl(args.gold),
            load_jsonl(args.badcases),
            top_n=args.top_n,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    write_json(args.out, report)
    write_markdown(args.markdown, render_markdown(report).splitlines())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run focused tests and refactor only after GREEN**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_analyze_non_procurement_gaps.py -q
.\.venv\Scripts\python.exe -m ruff check ..\scripts\analyze_non_procurement_gaps.py tests\test_analyze_non_procurement_gaps.py
cd ..
```

Expected: all analyzer tests pass and ruff reports no errors.

- [ ] **Step 5: Generate the first real gap report**

Run:

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py `
  --packages-root reports\real_world_packages `
  --gold examples\real_world\gold\mapping_gold.jsonl `
  --badcases examples\real_world\gold\real_world_badcases.jsonl `
  --out reports\non_procurement_gap_analysis.json `
  --markdown reports\non_procurement_gap_analysis.md
```

Expected: both reports exist, contain 20 non-procurement documents, and list all six gap arrays.

- [ ] **Step 6: Commit analyzer and generated evidence**

```powershell
git add scripts/analyze_non_procurement_gaps.py backend/tests/test_analyze_non_procurement_gaps.py reports/non_procurement_gap_analysis.json reports/non_procurement_gap_analysis.md
git commit -m "feat: analyze non-procurement mapping gaps"
```

### Task 3: Add Traceable Non-procurement Candidates

**Files:**
- Create: `backend/tests/test_candidate_service_non_procurement.py`
- Modify: `backend/app/services/candidate_service.py`

- [ ] **Step 1: Write failing candidate extraction tests**

```python
from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService


def uir(blocks):
    return UIRDocument.model_validate({
        "uir_version": "1.0",
        "doc_id": "candidate-doc",
        "metadata": {"domain": "policy_doc"},
        "blocks": blocks,
        "assets": [],
        "normalization_records": [],
    })


def test_extracts_heading_title_path_key_value_list_and_regex_candidates():
    document = uir([
        {"block_id": "h1", "type": "heading", "text": "政策申报指南", "attributes": {"level": 1, "title_path": ["政策", "申报指南"]}},
        {"block_id": "p1", "type": "paragraph", "text": "发布机构：示例委员会"},
        {"block_id": "h2", "type": "heading", "text": "申请材料", "attributes": {"level": 2}},
        {"block_id": "l1", "type": "list", "attributes": {"items": ["申请表", "营业执照"]}},
        {"block_id": "p2", "type": "paragraph", "text": "文号：示委发〔2026〕12号"},
    ])

    candidates = CandidateService().extract_candidates("task-candidate", document)
    by_name = {}
    for candidate in candidates:
        by_name.setdefault(candidate.source_name, []).append(candidate)

    assert by_name["policy_title"][0].value_sample == "政策申报指南"
    assert by_name["title_path"][0].value_sample == "政策 / 申报指南"
    assert by_name["发布机构"][0].value_sample == "示例委员会"
    assert by_name["申请材料"][0].value_sample == "申请表\n营业执照"
    assert by_name["document_number"][0].value_sample == "示委发〔2026〕12号"
    assert all(item.source_blocks for name in ("policy_title", "title_path", "发布机构", "申请材料", "document_number") for item in by_name[name])
    assert any("heading" in evidence for evidence in by_name["policy_title"][0].evidence)


def test_ignores_noise_key_and_does_not_promote_ambiguous_date():
    document = uir([
        {"block_id": "p1", "type": "paragraph", "text": "备注：发布日期可能调整"},
        {"block_id": "p2", "type": "paragraph", "text": "发布日期：2026年7月1日"},
    ])
    candidates = CandidateService().extract_candidates("task-noise", document)

    assert all(candidate.source_name != "备注" for candidate in candidates)
    explicit = next(candidate for candidate in candidates if candidate.source_name == "发布日期")
    assert explicit.confidence <= 0.8
```

- [ ] **Step 2: Run tests and confirm RED**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_service_non_procurement.py -q
cd ..
```

Expected: FAIL because the requested block-derived candidates are absent.

- [ ] **Step 3: Add narrowly scoped helper constants and extraction methods**

Add to `CandidateService`:

```python
NOISE_KEYS = {"附件", "目录", "正文", "说明", "备注", "注"}
LIST_HEADINGS = {
    "申请材料", "办理材料", "办理流程", "申报流程",
    "会议决定", "议定事项", "政策措施", "工作要求",
}
KEY_VALUE_PATTERN = re.compile(
    r"^(?:[（(]?[一二三四五六七八九十]+[）)]|\\d+[.、])?\\s*"
    r"(?P<key>[\\u4e00-\\u9fa5A-Za-z_ ]{2,20})[:：]\\s*(?P<value>.{1,1000})$"
)
PARAGRAPH_PATTERNS = (
    ("document_number", re.compile(r"[\\u4e00-\\u9fa5]{1,10}[〔\\[]\\d{4}[〕\\]]\\d{1,5}号")),
    ("contact_phone", re.compile(r"(?:联系电话|联系方式|咨询电话)[:：]?\\s*([0-9\\-]{7,20})")),
    ("issuer", re.compile(r"(?:发布机构|发文机关|印发机关|制定机关)[:：]?\\s*([^\\n。；;]{2,50})")),
    ("meeting_date", re.compile(r"(?:会议时间|召开时间|会议于)[:：]?\\s*(\\d{4}年\\d{1,2}月\\d{1,2}日)")),
)
```

In the block loop, track the most recent heading, emit heading aliases
`document_title`, `policy_title`, `meeting_title`, and `guide_title` for the
first level-one heading, emit `title_path`, parse key/value paragraphs, merge
the next list below a recognized heading, and emit regex candidates. Pass a
new optional `confidence` argument through `_candidate`:

```python
def _candidate(
    self,
    task_id: str,
    uir: UIRDocument,
    source_path: str,
    source_name: str,
    value: Any,
    source_blocks: list[str],
    source_kind: str,
    seen_names: dict[str, int],
    confidence: float = 0.8,
) -> FieldCandidate:
    normalized_name = self.normalize_name(source_name)
    seen_names[normalized_name] = seen_names.get(normalized_name, 0) + 1
    suffix = seen_names[normalized_name]
    return FieldCandidate(
        candidate_id=f"cand_{task_id}_{self.sanitize(source_name)}_{suffix}",
        task_id=task_id,
        doc_id=uir.doc_id,
        source_path=source_path,
        source_name=source_name,
        display_name=source_name,
        value_sample=value,
        inferred_type=self.infer_type(value),
        source_blocks=source_blocks,
        confidence=confidence,
        evidence=[f"extracted from {source_kind}"],
    )
```

Use confidence `0.8` for explicit heading/key-value/list evidence and `0.72`
for paragraph regex candidates so extraction alone cannot bypass mapping
safety.

- [ ] **Step 4: Run focused and existing candidate regressions**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_service_non_procurement.py tests\test_candidate_mapping_services.py -q
.\.venv\Scripts\python.exe -m ruff check app\services\candidate_service.py tests\test_candidate_service_non_procurement.py
cd ..
```

Expected: all tests pass with no lint errors.

- [ ] **Step 5: Commit candidate extraction**

```powershell
git add backend/app/services/candidate_service.py backend/tests/test_candidate_service_non_procurement.py
git commit -m "feat: extract traceable non-procurement candidates"
```

### Task 4: Strengthen Templates Without Adding Invalid Targets

**Files:**
- Create: `backend/tests/test_non_procurement_templates.py`
- Modify: `examples/production_like/mapping_templates/general_doc_base_v1.json`
- Modify: `examples/production_like/mapping_templates/meeting_doc_base_v1.json`
- Modify: `examples/production_like/mapping_templates/policy_doc_base_v1.json`

- [ ] **Step 1: Write failing template target and alias tests**

```python
from app.services.schema_service import SchemaService
from app.services.template_service import TemplateService


def test_non_procurement_alias_and_regex_targets_exist_and_high_frequency_aliases_load():
    schemas = SchemaService()
    templates = TemplateService()
    expected = {
        "general_doc_base_v1": {
            "title": {"事项名称", "指南名称"},
            "application_materials": {"所需材料", "材料清单"},
            "process_steps": {"办理程序", "操作流程"},
        },
        "meeting_doc_base_v1": {
            "meeting_title": {"会议纪要", "常务会议"},
            "attendees": {"参会同志", "列席人员"},
            "chairperson": {"会议主持", "召集人"},
        },
        "policy_doc_base_v1": {
            "title": {"文件名称", "通知名称"},
            "issuer": {"发布机构", "主管部门"},
            "document_number": {"政策编号", "通知编号"},
            "target_audience": {"申报主体", "适用范围"},
        },
    }

    for template_id, aliases in expected.items():
        template = templates.load_template(template_id)
        fields = {field.field_id for field in schemas.load_schema(template.schema_id).fields}
        for target, required_aliases in aliases.items():
            assert required_aliases <= set(template.aliases[target])
        assert set(template.aliases) <= fields
        assert {rule.target_field_id for rule in template.regex_rules} <= fields


def test_general_contact_does_not_treat_contact_person_as_contact_value():
    template = TemplateService().load_template("general_doc_base_v1")
    assert "联系人" not in template.aliases["contact"]
```

- [ ] **Step 2: Run tests and confirm RED**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_non_procurement_templates.py -q
cd ..
```

Expected: FAIL on missing aliases and the unsafe `联系人` alias.

- [ ] **Step 3: Update only aliases whose target fields exist**

Add these aliases, preserving existing values and removing `联系人` from
`general_doc.contact`:

```json
{
  "general_doc": {
    "title": ["document_title", "guide_title", "事项名称", "服务事项", "办事事项", "项目名称", "通知标题", "指南名称", "业务名称"],
    "issuer": ["发布机构", "办理部门", "受理部门", "责任单位", "牵头单位", "实施单位", "服务机构"],
    "published_at": ["发布时间", "印发日期"],
    "service_object": ["面向对象", "申请对象", "办理对象", "支持对象", "申报对象"],
    "application_conditions": ["受理条件", "资格条件", "基本条件"],
    "application_materials": ["所需材料", "提交材料", "材料清单"],
    "process_steps": ["办理程序", "申请流程", "办事流程", "操作流程", "流程说明"],
    "contact": ["联系地址"]
  },
  "meeting_doc": {
    "meeting_title": ["会议纪要", "专题会议", "常务会议"],
    "attendees": ["参会同志", "出席同志", "参加人员", "列席人员", "参会单位"],
    "chairperson": ["主持", "会议主持", "召集人"],
    "topics": ["会议议程", "研究事项", "讨论事项"],
    "decisions": ["会议要求", "工作部署"],
    "action_items": ["下一步工作", "任务分工"]
  },
  "policy_doc": {
    "title": ["policy_title", "文件名称", "通知名称", "政策标题", "文件标题"],
    "issuer": ["发布机构", "主管部门", "牵头部门", "责任部门"],
    "document_number": ["政策编号", "通知编号"],
    "publish_date": ["发布时间", "公开日期"],
    "effective_date": ["施行日期", "执行日期"],
    "target_audience": ["适用范围", "支持对象", "申报主体", "面向对象"],
    "policy_measures": ["扶持措施", "重点任务", "工作措施", "具体措施"]
  }
}
```

Add regex rules in the repository's existing `target_field_id`/capture-group
format:

```json
[
  {
    "target_field_id": "document_number",
    "pattern": "(?P<value>[\\u4e00-\\u9fa5]{1,10}[〔\\[]\\d{4}[〕\\]]\\d{1,5}号)",
    "group": 1
  },
  {
    "target_field_id": "effective_date",
    "pattern": "(?:自|从)(?P<value>\\d{4}年\\d{1,2}月\\d{1,2}日)起(?:施行|实施|执行)",
    "group": 1
  }
]
```

Do not add guide aliases for `legal_basis`, `requirements`,
`application_process`, or `contact_phone` to policy templates because those
targets do not exist in `policy_doc_v1.json`.

- [ ] **Step 4: Run template and safety regressions**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_non_procurement_templates.py tests\test_non_procurement_schema_templates.py tests\test_general_doc_mapping_rules.py tests\test_meeting_doc_mapping_rules.py tests\test_policy_doc_mapping_rules.py tests\test_candidate_mapping_services.py -q
cd ..
```

Expected: all tests pass; fuzzy/badcase mappings remain review-required.

- [ ] **Step 5: Commit templates**

```powershell
git add backend/tests/test_non_procurement_templates.py examples/production_like/mapping_templates/general_doc_base_v1.json examples/production_like/mapping_templates/meeting_doc_base_v1.json examples/production_like/mapping_templates/policy_doc_base_v1.json
git commit -m "feat: expand safe non-procurement mapping templates"
```

### Task 5: Normalize Non-procurement Values

**Files:**
- Create: `backend/tests/test_non_procurement_transform.py`
- Modify: `backend/app/services/transform_service.py`

- [ ] **Step 1: Write failing transform tests**

```python
from app.schemas.target_schema import TargetField
from app.services.transform_service import TransformService


def field(field_id: str, field_type: str) -> TargetField:
    return TargetField(
        field_id=field_id,
        name=field_id,
        display_name=field_id,
        type=field_type,
        required=False,
        aliases=[],
        constraints={},
    )


def test_normalizes_spaced_and_dotted_dates():
    service = TransformService()
    assert service._coerce_value("2026 年 7 月 1 日", field("publish_date", "date"), {}) == ("2026-07-01", None)
    assert service._coerce_value("2026.7.1", field("meeting_date", "date"), {}) == ("2026-07-01", None)


def test_splits_supported_array_fields_and_cleans_contact():
    service = TransformService()
    assert service._coerce_value("张三、李四；王五", field("attendees", "array[string]"), {}) == (["张三", "李四", "王五"], None)
    assert service._coerce_value("021 - 12345678", field("contact", "string"), {}) == ("021-12345678", None)


def test_keeps_document_number_and_rejects_yearless_date():
    service = TransformService()
    assert service._coerce_value("沪府办发〔2026〕12号", field("document_number", "string"), {}) == ("沪府办发〔2026〕12号", None)
    value, error = service._coerce_value("7月1日", field("publish_date", "date"), {})
    assert value == "7月1日"
    assert error is not None
    assert error["code"] == "date_format_error"
```

- [ ] **Step 2: Run tests and confirm RED**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_non_procurement_transform.py -q
cd ..
```

Expected: FAIL on spaced/dotted dates, array splitting, and contact cleanup.

- [ ] **Step 3: Implement minimal field-aware coercion**

Add:

```python
SPLIT_ARRAY_FIELDS = {
    "attendees",
    "application_materials",
    "process_steps",
    "policy_measures",
    "requirements",
}
```

Update `_coerce_value` string and array branches:

```python
if field.type.startswith("array"):
    if isinstance(value, list):
        return value, None
    if isinstance(value, str) and field.field_id in self.SPLIT_ARRAY_FIELDS:
        items = [item.strip() for item in re.split(r"[、；;\n]+", value) if item.strip()]
        return items, None
    return [value], None
if field.field_id == "contact" and isinstance(value, str):
    return re.sub(r"\s*-\s*", "-", value).strip(), None
return value, None
```

Replace the date match with:

```python
match = re.fullmatch(
    r"(\d{4})\s*(?:[-/年.]|\s年\s*)\s*(\d{1,2})\s*"
    r"(?:[-/月.]|\s月\s*)\s*(\d{1,2})\s*(?:日)?",
    stripped,
)
```

- [ ] **Step 4: Run focused and conversion regressions**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_non_procurement_transform.py tests\test_conversion_artifact_services.py tests\test_procurement_mapping.py -q
.\.venv\Scripts\python.exe -m ruff check app\services\transform_service.py tests\test_non_procurement_transform.py
cd ..
```

Expected: all tests pass and lint is clean.

- [ ] **Step 5: Commit transform changes**

```powershell
git add backend/app/services/transform_service.py backend/tests/test_non_procurement_transform.py
git commit -m "feat: normalize non-procurement field values"
```

### Task 6: Lock Schema Safety and Extend Badcases

**Files:**
- Create: `backend/tests/test_non_procurement_schema_validation.py`
- Create: `reports/non_procurement_schema_adjustments.md`
- Create: `backend/tests/test_non_procurement_badcases.py`
- Modify: `examples/real_world/gold/real_world_badcases.jsonl`

- [ ] **Step 1: Write schema safety tests**

```python
from app.services.schema_service import SchemaService


def test_non_procurement_core_required_fields_remain_required():
    service = SchemaService()
    assert {field.field_id for field in service.get_required_fields(service.load_schema("general_doc"))} == {"title", "content"}
    assert {field.field_id for field in service.get_required_fields(service.load_schema("meeting_doc"))} == {"meeting_title", "meeting_date", "content"}
    assert {field.field_id for field in service.get_required_fields(service.load_schema("policy_doc"))} == {"title", "issuer", "publish_date", "content"}


def test_procurement_required_fields_are_unchanged():
    required = {field.field_id for field in SchemaService().get_required_fields(SchemaService().load_schema("procurement_doc"))}
    assert {"title", "project_name", "purchaser"} <= required
```

- [ ] **Step 2: Write badcase data and enforcement tests**

```python
import json
from pathlib import Path

from app.schemas.mapping import FieldCandidate
from app.services.mapping_service import MappingService
from app.services.schema_service import SchemaService
from app.services.template_service import TemplateService

ROOT = Path(__file__).resolve().parents[2]
BADCASES = ROOT / "examples" / "real_world" / "gold" / "real_world_badcases.jsonl"


def test_required_non_procurement_confusion_pairs_exist():
    rows = [json.loads(line) for line in BADCASES.read_text(encoding="utf-8").splitlines() if line.strip()]
    pairs = {
        (
            row["forbidden_auto_mapping"]["source_name"],
            row["forbidden_auto_mapping"]["target_field"],
        )
        for row in rows
    }
    assert ("发布日期", "effective_date") in pairs
    assert ("主持人", "attendees") in pairs
    assert ("联系人", "attendees") in pairs
    assert ("承办单位", "issuer") in pairs
    assert ("预算金额", "award_amount") in pairs
    assert ("控制价", "award_amount") in pairs


def test_badcase_pair_cannot_be_auto_accepted():
    from app.schemas.uir import UIRDocument

    policy_uir = UIRDocument.model_validate({
        "uir_version": "1.0",
        "doc_id": "policy-badcase",
        "metadata": {},
        "blocks": [{"block_id": "b1", "type": "paragraph", "text": "发布日期：2026-07-01"}],
        "assets": [],
        "normalization_records": [],
    })
    candidate = FieldCandidate(
        candidate_id="cand_bad_date",
        task_id="task_bad_date",
        doc_id=policy_uir.doc_id,
        source_path="$.blocks.b1.text",
        source_name="发布日期",
        value_sample="2026-07-01",
        inferred_type="date",
        source_blocks=["b1"],
        confidence=0.99,
        evidence=["explicit label"],
    )
    report = MappingService().map_fields(
        task_id="task_bad_date",
        uir=policy_uir,
        schema=SchemaService().load_schema("policy_doc"),
        template=TemplateService().load_template("policy_doc_base_v1"),
        candidates=[candidate],
        options={"badcases": [{"source_field": "发布日期", "forbidden_target_fields": ["effective_date"]}]},
    )
    assert all(
        not (item["target_field_id"] == "effective_date" and item["status"] == "accepted")
        for item in report.mappings
    )
```

- [ ] **Step 3: Run tests and confirm the badcase dataset test is RED**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_non_procurement_schema_validation.py tests\test_non_procurement_badcases.py -q
cd ..
```

Expected: schema tests pass; badcase dataset test fails because the generic
confusion pairs are not yet present.

- [ ] **Step 4: Add evidence-backed badcase rows**

Append JSONL rows using existing documents and actual source paths. Each row
must contain `case_id`, `doc_id`, `badcase_type`, `source_evidence`,
`forbidden_auto_mapping`, `expected_behavior`, and `severity`. Use these exact
forbidden pairs:

```json
{"source_name":"发布日期","target_field":"effective_date"}
{"source_name":"主持人","target_field":"attendees"}
{"source_name":"联系人","target_field":"attendees"}
{"source_name":"承办单位","target_field":"issuer"}
{"source_name":"预算金额","target_field":"award_amount"}
{"source_name":"控制价","target_field":"award_amount"}
```

For every row, point `source_evidence.source_paths` at a matching block or
table row in the selected real-world UIR and copy a short matching excerpt.
Do not invent a source path.

- [ ] **Step 5: Record the schema decision**

Create:

```markdown
# Non-procurement Schema Adjustments

| doc_type | field | old_rule | new_rule | reason | affected_docs | risk | reviewer_note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| general_doc | required fields | title, content | unchanged | Existing requirements are already limited to core identity and content fields. | 4 | none | Do not relax for metric gain. |
| meeting_doc | required fields | meeting_title, meeting_date, content | unchanged | These remain the minimum evidence-backed meeting representation. | 6 | missing dates remain visible | Improve extraction before reconsidering schema. |
| policy_doc | required fields | title, issuer, publish_date, content | unchanged | These remain the minimum evidence-backed policy representation. | 10 | missing issuer/date remain visible | Improve extraction and aliases before reconsidering schema. |

No `required` field was removed in this iteration.
```

- [ ] **Step 6: Run safety regressions and commit**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_non_procurement_schema_validation.py tests\test_non_procurement_badcases.py tests\test_candidate_mapping_services.py tests\test_procurement_mapping.py -q
cd ..
git add backend/tests/test_non_procurement_schema_validation.py backend/tests/test_non_procurement_badcases.py examples/real_world/gold/real_world_badcases.jsonl reports/non_procurement_schema_adjustments.md
git commit -m "test: protect non-procurement mapping boundaries"
```

Expected: all tests pass and badcase-blocked pairs remain review-required.

### Task 7: Add the Guide-compatible Dedicated Evaluator

**Files:**
- Create: `backend/tests/test_eval_non_procurement_mapping.py`
- Create: `scripts/eval_non_procurement_mapping.py`

- [ ] **Step 1: Write failing evaluator report tests**

```python
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "eval_non_procurement_mapping.py"


def load_module():
    spec = importlib.util.spec_from_file_location("eval_non_procurement_mapping", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_report_uses_required_contract_and_baseline_delta():
    module = load_module()
    items = [{
        "doc_id": "g1",
        "doc_type": "general_doc",
        "schema_id": "general_doc",
        "template_id": "general_doc_base_v1",
        "strict_passed": True,
        "package_passed": True,
        "required_missing": [],
        "review_evidence": [],
        "high_risk_auto_accepted": [],
        "metrics": {"mapping_recall": 0.75, "badcase_violation_count": 0},
        "mapped_or_review_targets": ["title", "content"],
    }]
    baseline = {
        "average_recall": 0.349,
        "review_required_count": 145,
        "required_missing_count": 18,
        "strict_pass_count": 4,
    }

    report = module.build_evaluation_report(items, baseline)

    assert report["summary"]["dataset_size"] == 1
    assert report["summary"]["strict_pass_count"] == 1
    assert report["summary"]["average_recall"] == 0.75
    assert report["summary"]["package_verify_pass_count"] == 1
    assert report["delta"]["average_recall"] == 0.401
    assert set(report) >= {"by_doc_type", "by_field", "typical_improvements", "remaining_gaps", "failed_cases"}
    markdown = module.render_markdown(report)
    for heading in (
        "## Summary",
        "## Metrics By Document Type",
        "## Field-level Recall",
        "## Strict Validation",
        "## Review-required Analysis",
        "## Required Missing Analysis",
        "## Badcase Safety",
        "## Typical Improvements",
        "## Remaining Gaps",
        "## Commands",
    ):
        assert heading in markdown
```

- [ ] **Step 2: Run test and confirm RED**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_eval_non_procurement_mapping.py -q
cd ..
```

Expected: FAIL because the new evaluator module does not exist.

- [ ] **Step 3: Reuse the existing evaluator instead of duplicating HTTP flow**

Create:

```python
"""Evaluate mapping recall for real non-procurement documents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eval_non_procurement_doc import (
    CATALOGS,
    _aggregate,
    _document,
    non_procurement_rows,
)
from eval_real_world_mapping import evaluate_rows
from eval_support import EvaluationHttpClient, load_jsonl, write_json, write_markdown

ROOT = Path(__file__).resolve().parents[1]


def build_evaluation_report(
    items: list[dict[str, Any]],
    baseline: dict[str, Any] | None,
) -> dict[str, Any]:
    documents = [_document(item) for item in items]
    aggregate = _aggregate(documents)
    summary = {
        "dataset_size": aggregate["document_count"],
        "strict_pass_count": aggregate["strict_pass_count"],
        "strict_pass_rate": aggregate["strict_pass_rate"],
        "average_recall": aggregate["mapping_recall_average"],
        "review_required_count": aggregate["review_required_count"],
        "required_missing_count": aggregate["required_missing_count"],
        "badcase_violation_count": aggregate["badcase_violation_count"],
        "package_verify_pass_count": aggregate["package_valid_count"],
    }
    by_doc_type = {
        doc_type: _aggregate([item for item in documents if item.get("doc_type") == doc_type])
        for doc_type in CATALOGS
    }
    by_field: list[dict[str, Any]] = []
    failed_cases = [
        {
            "doc_id": item.get("doc_id"),
            "doc_type": item.get("doc_type"),
            "reasons": item.get("failure_reasons", []),
        }
        for item in documents
        if item.get("failure_reasons")
    ]
    report = {
        "summary": summary,
        "by_doc_type": by_doc_type,
        "by_field": by_field,
        "typical_improvements": [],
        "remaining_gaps": failed_cases,
        "failed_cases": failed_cases,
    }
    if baseline:
        report["delta"] = {
            "average_recall": round(summary["average_recall"] - float(baseline.get("average_recall", 0.0)), 3),
            "review_required_count": summary["review_required_count"] - int(baseline.get("review_required_count", 0)),
            "required_missing_count": summary["required_missing_count"] - int(baseline.get("required_missing_count", 0)),
            "strict_pass_count": summary["strict_pass_count"] - int(baseline.get("strict_pass_count", 0)),
        }
    return report


def load_baseline(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Baseline must be an object: {path}")
    return value
```

Add this renderer and CLI, supporting both guide argument names
`--out`/`--markdown` and repository-compatible aliases
`--out-json`/`--out-md`:

```python
def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Non-procurement Mapping Evaluation Report",
        "",
        "## Summary",
        "",
        f"- Dataset size: {summary['dataset_size']}",
        f"- Strict pass: {summary['strict_pass_count']}",
        f"- Average recall: {summary['average_recall']:.3f}",
        f"- Review required: {summary['review_required_count']}",
        f"- Required missing: {summary['required_missing_count']}",
        f"- Badcase violations: {summary['badcase_violation_count']}",
        f"- Package verify pass: {summary['package_verify_pass_count']}",
        "",
        "## Metrics By Document Type",
        "",
    ]
    for doc_type, metrics in report["by_doc_type"].items():
        lines.append(
            f"- {doc_type}: documents={metrics['document_count']}, "
            f"strict_pass={metrics['strict_pass_count']}, "
            f"recall={metrics['mapping_recall_average']:.3f}"
        )
    for heading, key in (
        ("Field-level Recall", "by_field"),
        ("Strict Validation", "failed_cases"),
        ("Review-required Analysis", "remaining_gaps"),
        ("Required Missing Analysis", "remaining_gaps"),
        ("Badcase Safety", "failed_cases"),
        ("Typical Improvements", "typical_improvements"),
        ("Remaining Gaps", "remaining_gaps"),
    ):
        lines.extend(["", f"## {heading}", ""])
        rows = report[key]
        lines.append("- None" if not rows else f"- {len(rows)} item(s); see JSON report for details.")
    lines.extend([
        "",
        "## Commands",
        "",
        "`backend\\.venv\\Scripts\\python.exe scripts\\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60`",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key")
    parser.add_argument("--gold", type=Path, default=ROOT / "examples" / "real_world" / "gold" / "mapping_gold.jsonl")
    parser.add_argument("--uir-dir", type=Path, default=ROOT / "examples" / "real_world" / "uir")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--out", "--out-json", dest="out", type=Path, default=ROOT / "reports" / "non_procurement_mapping_eval_report.json")
    parser.add_argument("--markdown", "--out-md", dest="markdown", type=Path, default=ROOT / "reports" / "non_procurement_mapping_eval_report.md")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    rows = non_procurement_rows(load_jsonl(args.gold))
    client = EvaluationHttpClient(args.base_url, api_key=args.api_key, timeout=args.timeout)
    try:
        baseline = load_baseline(args.baseline)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    report = build_evaluation_report(
        evaluate_rows(rows, client=client, uir_dir=args.uir_dir),
        baseline,
    )
    write_json(args.out, report)
    write_markdown(args.markdown, render_markdown(report).splitlines())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run focused evaluator tests and lint**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_eval_non_procurement_mapping.py tests\test_real_world_mapping_eval.py -q
.\.venv\Scripts\python.exe -m ruff check ..\scripts\eval_non_procurement_mapping.py tests\test_eval_non_procurement_mapping.py
cd ..
```

Expected: all tests pass and ruff is clean.

- [ ] **Step 5: Run the evaluator against the live API**

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60 `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\non_procurement_mapping_eval_report.json `
  --markdown reports\non_procurement_mapping_eval_report.md
```

Expected: 20 evaluated documents, 20 package verifications, zero badcase
violations, and explicit delta values.

- [ ] **Step 6: Commit evaluator and reports**

```powershell
git add scripts/eval_non_procurement_mapping.py backend/tests/test_eval_non_procurement_mapping.py reports/non_procurement_mapping_eval_report.json reports/non_procurement_mapping_eval_report.md
git commit -m "feat: evaluate non-procurement mapping recall"
```

### Task 8: Diagnose Results and Publish the Ranked Improvement Plan

**Files:**
- Create: `docs/non_procurement_mapping_improvement_plan.md`
- Regenerate: gap and evaluation reports

- [ ] **Step 1: Re-run the gap analyzer against post-change packages**

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py `
  --packages-root reports\real_world_packages `
  --gold examples\real_world\gold\mapping_gold.jsonl `
  --badcases examples\real_world\gold\real_world_badcases.jsonl `
  --out reports\non_procurement_gap_analysis.json `
  --markdown reports\non_procurement_gap_analysis.md
```

Expected: report generation succeeds and ranks remaining gaps.

- [ ] **Step 2: Write the evidence-ranked improvement plan**

Use this exact structure. Copy ranked rows from `recommended_plan`; exclude
any row whose source blocks are empty:

```markdown
# Non-procurement Mapping Improvement Plan

## Baseline

Average recall 0.3494; review-required 145; required missing 18; strict pass 4/20; badcase violations 0.

## High-frequency Fix Items

| ID | doc_type | target_field | count | gap_type | action | files_to_change | risk | expected_gain |
| --- | --- | --- | ---: | --- | --- | --- | --- | --- |

## Candidate Extraction Fixes
## Template Alias Fixes
## Regex Rule Fixes
## Schema Adjustments
## Transform Fixes
## Badcase Additions
## Verification Commands
```

- [ ] **Step 3: Record rejected automatic-rule recommendations**

Add a `## Rejected Automatic Rules` section. Copy every recommendation meeting
one of these conditions and state the matching reason:

```text
source_block_ids is empty
source label is generic metadata
the pair appears in badcases
the target does not exist in the schema
the proposed fix maps authored/published/effective dates without an explicit label
the proposed fix maps chairperson/contact person to attendees
```

- [ ] **Step 4: Re-run the evaluator after the planned implementation**

```powershell
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py `
  --base-url http://127.0.0.1:8000 `
  --timeout 60 `
  --baseline reports\non_procurement_baseline_report.json `
  --out reports\non_procurement_mapping_eval_report.json `
  --markdown reports\non_procurement_mapping_eval_report.md
```

Expected: the report truthfully records the new metrics; badcase violations
remain zero. Do not claim phase-one success unless all thresholds pass.

- [ ] **Step 5: Commit the ranked diagnosis**

Stage only the improvement plan, regenerated reports, and any focused
rule/test files actually changed:

```powershell
git add docs/non_procurement_mapping_improvement_plan.md reports/non_procurement_gap_analysis.json reports/non_procurement_gap_analysis.md reports/non_procurement_mapping_eval_report.json reports/non_procurement_mapping_eval_report.md
git commit -m "feat: apply evidence-backed mapping recall fixes"
```

### Task 9: Update Acceptance Evidence and Documentation

**Files:**
- Create: `reports/non_procurement_acceptance_report.md`
- Modify: `README.md`
- Modify: `docs/final_handoff_status.md`
- Modify: `docs/requirement_mapping.md`
- Modify: `docs/real_world_uir_dataset.md`
- Modify: `docs/badcase_analysis.md`
- Modify: `docs/developer_guide.md`

- [ ] **Step 1: Build the acceptance table from fresh report values**

```markdown
# Non-procurement Mapping Recall Acceptance Report

## Result

| Check | Target | Actual | Status |
| --- | ---: | ---: | --- |
| Average recall | >= 0.50 | value from report | PASS or NOT MET |
| Review-required | <= 115 | value from report | PASS or NOT MET |
| Required missing | <= 14 | value from report | PASS or NOT MET |
| Badcase violations | 0 | value from report | PASS or NOT MET |
| Package verification | 20/20 | value from report | PASS or NOT MET |
| Backend tests | pass | value from verification | PASS or NOT MET |
| Frontend build | pass | value from verification | PASS or NOT MET |
| verify_all | pass | value from verification | PASS or NOT MET |

## Changes

- Gap analyzer and dedicated evaluator
- Evidence-backed candidate extraction
- Schema-valid aliases and regex rules
- Field-aware transforms
- Expanded badcase protection

## Remaining Risks

List the top remaining candidate, alias, regex, transform, and schema gaps from the generated gap report.
```

- [ ] **Step 2: Update required documents with commands and truthful metrics**

Add compact sections that link to the baseline, gap analysis, evaluation, and
acceptance reports. State whether phase one is met. Include the evaluator and
analyzer commands in `docs/developer_guide.md`. Record the added badcase
categories in `docs/badcase_analysis.md`. Record the 20-document type split
and report paths in `docs/real_world_uir_dataset.md`.

- [ ] **Step 3: Check documentation for unsupported success language**

Run:

```powershell
rg -n "已完全解决非采购类映射问题|字段映射准确率已达 85%|所有非采购文档均严格通过" README.md docs reports\non_procurement_acceptance_report.md
```

Expected: no matches unless the fresh reports literally prove the statement.

- [ ] **Step 4: Commit documentation**

```powershell
git add README.md docs/final_handoff_status.md docs/requirement_mapping.md docs/real_world_uir_dataset.md docs/badcase_analysis.md docs/developer_guide.md reports/non_procurement_acceptance_report.md
git commit -m "docs: report non-procurement recall results"
```

### Task 10: Run Full Verification

**Files:**
- Regenerate verified reports only when their commands succeed.

- [ ] **Step 1: Run backend tests and lint**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
cd ..
```

Expected: zero test failures and zero lint violations.

- [ ] **Step 2: Run a clean frontend build**

```powershell
cd frontend
npm ci
npm run build
cd ..
```

Expected: both commands exit `0`.

- [ ] **Step 3: Run unified verification**

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

Expected: exit `0`.

- [ ] **Step 4: Run API-backed evaluators**

```powershell
backend\.venv\Scripts\python.exe scripts\eval_real_world_uir.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_real_world_mapping.py --base-url http://127.0.0.1:8000 --timeout 60
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json
```

Expected: all commands exit `0`, package verification is complete, and
badcase violations remain zero.

- [ ] **Step 5: Run analyzer and secondary regressions**

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py --packages-root reports\real_world_packages --gold examples\real_world\gold\mapping_gold.jsonl --badcases examples\real_world\gold\real_world_badcases.jsonl --out reports\non_procurement_gap_analysis.json --markdown reports\non_procurement_gap_analysis.md
backend\.venv\Scripts\python.exe scripts\eval_content_strategy_comparison.py
backend\.venv\Scripts\python.exe scripts\eval_summary_faithfulness.py
backend\.venv\Scripts\python.exe scripts\eval_content_tag_quality.py
backend\.venv\Scripts\python.exe scripts\eval_review_knowledge_growth.py
backend\.venv\Scripts\python.exe scripts\verify_downstream_contract.py --packages-root reports\real_world_packages --out reports\downstream_contract_eval_report.json --markdown reports\downstream_contract_eval_report.md
```

Expected: all commands exit `0`.

- [ ] **Step 6: Verify acceptance and repository state**

```powershell
git status --short
git log --oneline -10
```

Compare every acceptance-report value with
`reports/non_procurement_mapping_eval_report.json`. Amend the documentation
commit if any value differs. Leave the user's two untracked guide documents
untouched.
