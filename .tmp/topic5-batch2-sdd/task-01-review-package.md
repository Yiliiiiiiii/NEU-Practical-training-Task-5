# Task 01 working-tree review package
Base/HEAD: 661ad4480cfe4aa4982def583c83770c1521707a (commit blocked; review scoped working-tree changes)

## Tracked diff
diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
index 6c87b439..5e2e2cef 100644
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -1,42 +1,37 @@
 name: CI
 
 on:
   push:
   pull_request:
 
 jobs:
-  backend:
-    runs-on: windows-latest
+  topic5-batch-2-verification:
+    strategy:
+      fail-fast: false
+      matrix:
+        os: [windows-latest, ubuntu-latest]
+    runs-on: ${{ matrix.os }}
     steps:
       - uses: actions/checkout@v4
       - uses: actions/setup-python@v5
         with:
-          python-version: "3.11"
-      - name: Install backend dependencies
-        run: |
-          cd backend
-          python -m pip install -r requirements.txt
-      - name: Ruff
-        run: |
-          cd backend
-          python -m ruff check .
-      - name: Pytest
-        run: |
-          cd backend
-          python -m pytest -q
-
-  frontend:
-    runs-on: windows-latest
-    steps:
-      - uses: actions/checkout@v4
+          python-version: "3.13"
       - uses: actions/setup-node@v4
         with:
           node-version: "20"
+          cache: npm
+          cache-dependency-path: frontend/package-lock.json
+      - name: Install backend dependencies
+        run: python -m pip install -r backend/requirements.txt
       - name: Install frontend dependencies
-        run: |
-          cd frontend
-          npm install
-      - name: Build frontend
-        run: |
-          cd frontend
-          npm run build
+        working-directory: frontend
+        run: npm ci
+      - name: Run Topic 5 Batch 2 verification
+        run: python scripts/run_topic5_batch_2_verification.py
+      - name: Upload verification evidence
+        if: always()
+        uses: actions/upload-artifact@v4
+        with:
+          name: topic5-batch-2-${{ runner.os }}
+          path: reports/topic5_batch_2/verification
+          if-no-files-found: warn
diff --git a/backend/tests/test_openapi_export.py b/backend/tests/test_openapi_export.py
index a277d95b..dad414b0 100644
--- a/backend/tests/test_openapi_export.py
+++ b/backend/tests/test_openapi_export.py
@@ -26,10 +26,25 @@ def test_openapi_export_includes_demo_workflow_paths(tmp_path):
     for path in [
         "/api/v1/documents/import",
         "/api/v1/schemas",
         "/api/v1/templates",
         "/api/v1/tasks",
         "/api/v1/tasks/{task_id}/execute",
         "/api/v1/tasks/{task_id}/reports/{report_name}",
         "/api/v1/tasks/{task_id}/package/download",
     ]:
         assert path in schema["paths"]
+
+
+def test_openapi_check_detects_drift_without_rewriting_expected_file(tmp_path):
+    module = load_export_module()
+    expected = tmp_path / "openapi.json"
+    module.export_openapi(expected)
+    original = expected.read_bytes()
+
+    assert module.check_openapi_drift(expected) is True
+    assert expected.read_bytes() == original
+
+    expected.write_text("{}\n", encoding="utf-8")
+    drifted = expected.read_bytes()
+    assert module.check_openapi_drift(expected) is False
+    assert expected.read_bytes() == drifted
diff --git a/backend/tests/test_topic5_hard_gap_evaluators.py b/backend/tests/test_topic5_hard_gap_evaluators.py
index 9306c0cb..2fdaaf6c 100644
--- a/backend/tests/test_topic5_hard_gap_evaluators.py
+++ b/backend/tests/test_topic5_hard_gap_evaluators.py
@@ -1,18 +1,21 @@
 from __future__ import annotations
 
 import copy
 import json
 from pathlib import Path
 
 import pytest
-from scripts.check_topic5_hard_gap_batch_1_gate import evaluate_gate
+from scripts.check_topic5_hard_gap_batch_1_gate import (
+    build_evaluator_reports,
+    evaluate_gate,
+)
 from scripts.eval_topic5_field_operations import build_report as field_report
 from scripts.eval_topic5_field_operations import load_fixture as load_field_fixture
 from scripts.eval_topic5_schema_localization import (
     build_report as localization_report,
 )
 from scripts.eval_topic5_schema_localization import (
     load_fixture as load_localization_fixture,
 )
 
 ROOT = Path(__file__).resolve().parents[2]
@@ -77,31 +80,34 @@ def test_gate_passes_all_thresholds_and_fails_mutated_metric() -> None:
     components = {
         name: {"passed": True}
         for name in ("metadata", "summary", "consistency", "entity", "topic11", "legacy")
     }
     verification = {
         "full_backend_tests_passed": True,
         "ruff_clean": True,
         "frontend_tests_passed": True,
         "openapi_export_passed": True,
     }
+    evaluator_reports = build_evaluator_reports()
 
     passed = evaluate_gate(
         operations=operations,
         localization=localization,
         tag_quality=tag_quality,
         components=components,
+        evaluator_reports=evaluator_reports,
         verification=verification,
     )
     assert passed["conclusion"] == "passed"
 
     failed_operations = copy.deepcopy(operations)
     failed_operations["merge_accuracy"] = 0.94
     failed = evaluate_gate(
         operations=failed_operations,
         localization=localization,
         tag_quality=tag_quality,
         components=components,
+        evaluator_reports=evaluator_reports,
         verification=verification,
     )
     assert failed["conclusion"] == "failed"
     assert failed["failed_conditions"] == ["merge_accuracy"]
diff --git a/scripts/check_topic5_hard_gap_batch_1_gate.py b/scripts/check_topic5_hard_gap_batch_1_gate.py
index fcd4b7a6..b93b6e83 100644
--- a/scripts/check_topic5_hard_gap_batch_1_gate.py
+++ b/scripts/check_topic5_hard_gap_batch_1_gate.py
@@ -9,23 +9,38 @@ import sys
 from datetime import UTC, datetime
 from pathlib import Path
 from typing import Any
 
 ROOT = Path(__file__).resolve().parents[1]
 BACKEND = ROOT / "backend"
 if str(ROOT) not in sys.path:
     sys.path.insert(0, str(ROOT))
 
 from scripts.eval_topic5_field_operations import build_report as field_report  # noqa: E402
+from scripts.eval_topic5_artifact_consistency import (  # noqa: E402
+    build_report as artifact_consistency_report,
+)
+from scripts.eval_topic5_entity_passthrough import (  # noqa: E402
+    build_report as entity_passthrough_report,
+)
+from scripts.eval_topic5_metadata_contract import (  # noqa: E402
+    build_report as metadata_contract_report,
+)
 from scripts.eval_topic5_schema_localization import (  # noqa: E402
     build_report as localization_report,
 )
+from scripts.eval_topic5_summary_faithfulness import (  # noqa: E402
+    build_report as summary_faithfulness_report,
+)
+from scripts.eval_topic5_topic11_adapter import (  # noqa: E402
+    build_report as topic11_adapter_report,
+)
 
 DEFAULT_OUTPUT = ROOT / "docs" / "交接" / "evidence" / "hard_gap_batch_1" / "operations"
 DEFAULT_TAG_REPORT = ROOT / "docs" / "交接" / "evidence" / "hard_gap_batch_1" / "tags" / "content_tag_quality.json"
 DEFAULT_VERIFICATION = DEFAULT_OUTPUT / "verification_summary.json"
 
 COMPONENT_TESTS = {
     "metadata": [
         "backend/tests/test_metadata_template_service.py",
         "backend/tests/test_topic5_convert_api.py",
     ],
@@ -39,27 +54,34 @@ COMPONENT_TESTS = {
         "backend/tests/test_topic5_entity_passthrough.py",
     ],
     "topic11": [
         "backend/tests/test_topic11_chunk_provider.py",
     ],
     "legacy": [
         "backend/tests/test_package_1_1_assertion_report_compatibility.py",
         "backend/tests/test_topic5_convert_api.py",
     ],
 }
+EVALUATOR_BUILDERS = {
+    "metadata": metadata_contract_report,
+    "summary": summary_faithfulness_report,
+    "consistency": artifact_consistency_report,
+    "entity": entity_passthrough_report,
+    "topic11": topic11_adapter_report,
+}
 
 
 def run_component_checks() -> dict[str, dict[str, Any]]:
     results: dict[str, dict[str, Any]] = {}
     for name, paths in COMPONENT_TESTS.items():
         command = [
-            str(BACKEND / ".venv" / "Scripts" / "python.exe"),
+            sys.executable,
             "-m",
             "pytest",
             *paths,
             "-q",
         ]
         completed = subprocess.run(
             command,
             cwd=ROOT,
             capture_output=True,
             text=True,
@@ -67,62 +89,135 @@ def run_component_checks() -> dict[str, dict[str, Any]]:
         )
         results[name] = {
             "passed": completed.returncode == 0,
             "return_code": completed.returncode,
             "command": " ".join(command),
             "summary": _last_nonempty_line(completed.stdout or completed.stderr),
         }
     return results
 
 
+def build_evaluator_reports() -> dict[str, dict[str, Any]]:
+    return {name: builder() for name, builder in EVALUATOR_BUILDERS.items()}
+
+
+def skipped_component_checks() -> dict[str, dict[str, Any]]:
+    return {
+        name: {
+            "passed": False,
+            "status": "skipped",
+            "return_code": None,
+            "summary": "skipped by caller",
+        }
+        for name in COMPONENT_TESTS
+    }
+
+
+def _validated_evaluator_reports(
+    reports: dict[str, dict[str, Any]] | None,
+) -> dict[str, dict[str, Any]]:
+    reports = reports or {}
+    missing = sorted(EVALUATOR_BUILDERS.keys() - reports.keys())
+    if missing:
+        raise ValueError(f"missing evaluator report(s): {', '.join(missing)}")
+    for name in EVALUATOR_BUILDERS:
+        report = reports[name]
+        required = {
+            "dataset_id",
+            "dataset_version",
+            "dataset_sha256",
+            "commit_sha",
+            "case_count",
+            "passed_count",
+            "failed_cases",
+            "reproduction_command",
+            "claim_boundary",
+        }
+        absent = sorted(required - report.keys())
+        if absent:
+            raise ValueError(
+                f"{name} evaluator report is missing field(s): {', '.join(absent)}"
+            )
+        case_count = report["case_count"]
+        passed_count = report["passed_count"]
+        if (
+            not isinstance(case_count, int)
+            or isinstance(case_count, bool)
+            or case_count <= 0
+            or not isinstance(passed_count, int)
+            or isinstance(passed_count, bool)
+            or not 0 <= passed_count <= case_count
+        ):
+            raise ValueError(f"{name} evaluator report has invalid case accounting")
+    return reports
+
+
 def evaluate_gate(
     *,
     operations: dict[str, Any],
     localization: dict[str, Any],
     tag_quality: dict[str, Any],
     components: dict[str, dict[str, Any]],
+    evaluator_reports: dict[str, dict[str, Any]] | None = None,
     verification: dict[str, Any],
 ) -> dict[str, Any]:
     metrics = tag_quality.get("metrics", {})
-
-    def passed(name: str) -> bool:
-        return bool(components.get(name, {}).get("passed"))
+    reports = _validated_evaluator_reports(evaluator_reports)
+    metadata = reports["metadata"]
+    summary = reports["summary"]
+    consistency = reports["consistency"]
+    entity = reports["entity"]
+    topic11 = reports["topic11"]
 
     values = {
-        "metadata_template_effective": passed("metadata"),
-        "metadata_required_localization_rate": 1.0 if passed("metadata") else 0.0,
+        "metadata_template_effective": bool(metadata["metadata_template_effective"]),
+        "metadata_required_localization_rate": float(
+            metadata["metadata_required_localization_rate"]
+        ),
         "content_tag_metric": float(metrics.get("content_tag_f1", 0.0)),
         "management_tag_rule_accuracy": float(metrics.get("management_tag_f1", 0.0)),
         "quality_tag_metric": float(metrics.get("quality_tag_f1", 0.0)),
         "global_quality_tag_pollution_count": int(metrics.get("unknown_tag_count", -1)),
-        "document_summary_faithfulness": 1.0 if passed("summary") else 0.0,
-        "document_summary_source_coverage": 1.0 if passed("summary") else 0.0,
-        "document_summary_new_fact_violations": 0 if passed("summary") else 1,
-        "artifact_consistency_pass_rate": 1.0 if passed("consistency") else 0.0,
-        "markdown_block_coverage": 1.0 if passed("consistency") else 0.0,
-        "chunk_source_coverage": 1.0 if passed("consistency") else 0.0,
-        "tampering_detection_rate": 1.0 if passed("consistency") else 0.0,
-        "entity_passthrough_coverage": 1.0 if passed("entity") else 0.0,
-        "invented_entity_id_count": 0 if passed("entity") else 1,
-        "topic11_invalid_output_acceptance_count": 0 if passed("topic11") else 1,
-        "topic11_fallback_success_rate": 1.0 if passed("topic11") else 0.0,
-        "secret_leak_count": 0 if passed("topic11") else 1,
+        "document_summary_faithfulness": float(
+            summary["document_summary_faithfulness"]
+        ),
+        "document_summary_source_coverage": float(
+            summary["document_summary_source_coverage"]
+        ),
+        "document_summary_new_fact_violations": int(
+            summary["document_summary_new_fact_violations"]
+        ),
+        "artifact_consistency_pass_rate": float(
+            consistency["artifact_consistency_pass_rate"]
+        ),
+        "markdown_block_coverage": float(consistency["markdown_block_coverage"]),
+        "chunk_source_coverage": float(consistency["chunk_source_coverage"]),
+        "tampering_detection_rate": float(consistency["tampering_detection_rate"]),
+        "entity_passthrough_coverage": float(entity["entity_passthrough_coverage"]),
+        "invented_entity_id_count": int(entity["invented_entity_id_count"]),
+        "topic11_invalid_output_acceptance_count": int(
+            topic11["topic11_invalid_output_acceptance_count"]
+        ),
+        "topic11_fallback_success_rate": float(
+            topic11["topic11_fallback_success_rate"]
+        ),
+        "secret_leak_count": int(topic11["secret_leak_count"]),
         "field_operation_accuracy": float(operations["field_operation_accuracy"]),
         "rename_accuracy": float(operations["rename_accuracy"]),
         "merge_accuracy": float(operations["merge_accuracy"]),
         "split_accuracy": float(operations["split_accuracy"]),
         "unsafe_operation_count": int(operations["unsafe_operation_count"]),
         "schema_localization_rate": float(localization["schema_localization_rate"]),
         "error_code_accuracy": float(localization["error_code_accuracy"]),
         "stage_accuracy": float(localization["stage_accuracy"]),
-        "legacy_request_regression": 0 if passed("legacy") else 1,
-        "legacy_package_regression": 0 if passed("legacy") else 1,
+        "legacy_request_regression": int(topic11["legacy_request_regression"]),
+        "legacy_package_regression": int(topic11["legacy_package_regression"]),
         "full_backend_tests_passed": bool(verification.get("full_backend_tests_passed")),
         "ruff_clean": bool(verification.get("ruff_clean")),
         "frontend_tests_passed": bool(verification.get("frontend_tests_passed")),
         "openapi_export_passed": bool(verification.get("openapi_export_passed")),
     }
     checks = {
         "metadata_template_effective": values["metadata_template_effective"] is True,
         "metadata_required_localization_rate": values["metadata_required_localization_rate"] == 1.0,
         "content_tag_metric": values["content_tag_metric"] >= 0.85,
         "management_tag_rule_accuracy": values["management_tag_rule_accuracy"] == 1.0,
@@ -159,22 +254,27 @@ def evaluate_gate(
     return {
         "generated_at": datetime.now(UTC).isoformat(),
         "conclusion": "passed" if not failed else "failed",
         "passed": not failed,
         "values": values,
         "checks": checks,
         "failed_conditions": failed,
         "datasets": {
             "field_operations": operations["dataset_sha256"],
             "schema_localization": localization["dataset_sha256"],
+            **{
+                name: report["dataset_sha256"]
+                for name, report in reports.items()
+            },
         },
         "component_checks": components,
+        "evaluator_reports": reports,
     }
 
 
 def render_markdown(report: dict[str, Any]) -> str:
     lines = [
         "# Topic 5 Hard-Gap Batch 1 Gate",
         "",
         f"Conclusion: **{report['conclusion']}**",
         "",
         "| Condition | Value | Passed |",
@@ -195,29 +295,30 @@ def _last_nonempty_line(value: str) -> str:
 def main() -> None:
     parser = argparse.ArgumentParser(description=__doc__)
     parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
     parser.add_argument("--tag-report", type=Path, default=DEFAULT_TAG_REPORT)
     parser.add_argument("--verification", type=Path, default=DEFAULT_VERIFICATION)
     parser.add_argument("--skip-component-tests", action="store_true")
     args = parser.parse_args()
     if not args.verification.is_file():
         raise SystemExit(f"verification summary is missing: {args.verification}")
     components = (
-        {name: {"passed": True, "summary": "skipped by caller"} for name in COMPONENT_TESTS}
+        skipped_component_checks()
         if args.skip_component_tests
         else run_component_checks()
     )
     report = evaluate_gate(
         operations=field_report(),
         localization=localization_report(),
         tag_quality=json.loads(args.tag_report.read_text(encoding="utf-8")),
         components=components,
+        evaluator_reports=build_evaluator_reports(),
         verification=json.loads(args.verification.read_text(encoding="utf-8")),
     )
     args.out_dir.mkdir(parents=True, exist_ok=True)
     (args.out_dir / "hard_gap_batch_1_gate.json").write_text(
         json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
         encoding="utf-8",
     )
     (args.out_dir / "hard_gap_batch_1_gate.md").write_text(
         render_markdown(report), encoding="utf-8"
     )
diff --git a/scripts/export_openapi.py b/scripts/export_openapi.py
index 63f0fd2e..80dcc5d3 100644
--- a/scripts/export_openapi.py
+++ b/scripts/export_openapi.py
@@ -8,35 +8,54 @@ from typing import Any
 
 
 ROOT = Path(__file__).resolve().parents[1]
 BACKEND_DIR = ROOT / "backend"
 if str(BACKEND_DIR) not in sys.path:
     sys.path.insert(0, str(BACKEND_DIR))
 
 from app.main import create_app  # noqa: E402
 
 
+def _serialized_schema(schema: dict[str, Any]) -> str:
+    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
+
+
 def export_openapi(output_path: Path) -> dict[str, Any]:
     schema = create_app().openapi()
     output_path.parent.mkdir(parents=True, exist_ok=True)
-    output_path.write_text(
-        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
-        encoding="utf-8",
-    )
+    output_path.write_text(_serialized_schema(schema), encoding="utf-8")
     return schema
 
 
+def check_openapi_drift(expected_path: Path) -> bool:
+    if not expected_path.is_file():
+        return False
+    actual = _serialized_schema(create_app().openapi())
+    return expected_path.read_text(encoding="utf-8") == actual
+
+
 def main() -> None:
     parser = argparse.ArgumentParser(description=__doc__)
     parser.add_argument(
         "--output",
         type=Path,
         default=ROOT / "docs" / "openapi.json",
         help="Path to write the OpenAPI JSON schema.",
     )
+    parser.add_argument(
+        "--check",
+        action="store_true",
+        help="Exit nonzero when the committed OpenAPI JSON differs; do not rewrite it.",
+    )
     args = parser.parse_args()
+    if args.check:
+        if not check_openapi_drift(args.output):
+            print(f"OpenAPI drift detected for {args.output}")
+            raise SystemExit(1)
+        print(f"OpenAPI schema is current: {args.output}")
+        return
     schema = export_openapi(args.output)
     print(f"exported {len(schema.get('paths', {}))} paths to {args.output}")
 
 
 if __name__ == "__main__":
     main()

## Full file: scripts/topic5_eval_common.py
    1: """Shared report utilities for case-level Topic 5 evaluators."""
    2: 
    3: from __future__ import annotations
    4: 
    5: import hashlib
    6: import json
    7: import subprocess
    8: from datetime import UTC, datetime
    9: from pathlib import Path
   10: from typing import Any
   11: 
   12: 
   13: ROOT = Path(__file__).resolve().parents[1]
   14: 
   15: 
   16: def load_case_fixture(path: Path, *, dataset_id: str) -> dict[str, Any]:
   17:     payload = json.loads(path.read_text(encoding="utf-8"))
   18:     cases = payload.get("cases")
   19:     if payload.get("dataset_id") != dataset_id:
   20:         raise ValueError(f"expected dataset_id {dataset_id}")
   21:     if payload.get("version") != "2.0.0" or not isinstance(cases, list) or not cases:
   22:         raise ValueError("Topic 5 evaluator fixture must be non-empty version 2.0.0")
   23:     case_ids = [case.get("case_id") for case in cases]
   24:     if any(not case_id for case_id in case_ids) or len(case_ids) != len(set(case_ids)):
   25:         raise ValueError("Topic 5 evaluator case_id values must be non-empty and unique")
   26:     return payload
   27: 
   28: 
   29: def build_case_report(
   30:     *,
   31:     fixture_path: Path,
   32:     fixture: dict[str, Any],
   33:     cases: list[dict[str, Any]],
   34:     metrics: dict[str, Any],
   35:     reproduction_command: str,
   36:     claim_boundary: str,
   37: ) -> dict[str, Any]:
   38:     passed_count = sum(bool(case["passed"]) for case in cases)
   39:     return {
   40:         "dataset_id": fixture["dataset_id"],
   41:         "dataset_version": fixture["version"],
   42:         "dataset_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
   43:         "commit_sha": current_commit_sha(),
   44:         "generated_at": datetime.now(UTC).isoformat(),
   45:         "case_count": len(cases),
   46:         "passed_count": passed_count,
   47:         **metrics,
   48:         "failed_cases": [case for case in cases if not case["passed"]],
   49:         "cases": cases,
   50:         "reproduction_command": reproduction_command,
   51:         "claim_boundary": claim_boundary,
   52:     }
   53: 
   54: 
   55: def current_commit_sha() -> str:
   56:     completed = subprocess.run(
   57:         ["git", "rev-parse", "HEAD"],
   58:         cwd=ROOT,
   59:         check=True,
   60:         capture_output=True,
   61:         text=True,
   62:     )
   63:     return completed.stdout.strip()
   64: 
   65: 
   66: def write_json_report(report: dict[str, Any], path: Path) -> None:
   67:     path.parent.mkdir(parents=True, exist_ok=True)
   68:     path.write_text(
   69:         json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
   70:         encoding="utf-8",
   71:     )

## Full file: scripts/eval_topic5_metadata_contract.py
    1: """Evaluate Topic 5 metadata-template behavior with declared case expectations."""
    2: 
    3: from __future__ import annotations
    4: 
    5: import argparse
    6: import sys
    7: from pathlib import Path
    8: from typing import Any
    9: 
   10: 
   11: ROOT = Path(__file__).resolve().parents[1]
   12: BACKEND = ROOT / "backend"
   13: for import_path in (ROOT, BACKEND):
   14:     if str(import_path) not in sys.path:
   15:         sys.path.insert(0, str(import_path))
   16: 
   17: from app.schemas.metadata_template import MetadataTemplateConfig  # noqa: E402
   18: from app.schemas.uir import UIRDocument  # noqa: E402
   19: from app.services.metadata_template_service import MetadataTemplateService  # noqa: E402
   20: from scripts.topic5_eval_common import (  # noqa: E402
   21:     build_case_report,
   22:     load_case_fixture,
   23:     write_json_report,
   24: )
   25: 
   26: 
   27: DEFAULT_FIXTURE = ROOT / "eval" / "topic5_metadata_contract" / "v2" / "cases.json"
   28: DEFAULT_OUTPUT = ROOT / "reports" / "topic5_batch_2" / "metadata_contract.json"
   29: DATASET_ID = "topic5_metadata_contract"
   30: 
   31: 
   32: def load_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
   33:     return load_case_fixture(path, dataset_id=DATASET_ID)
   34: 
   35: 
   36: def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
   37:     template = MetadataTemplateConfig.model_validate(
   38:         {
   39:             "template_id": f"{case['case_id']}-template",
   40:             "schema_id": "topic5_metadata_eval",
   41:             "version": "2.0.0",
   42:             "metadata_fields": case["metadata_fields"],
   43:         }
   44:     )
   45:     result = MetadataTemplateService().render(
   46:         uir=UIRDocument.model_validate(
   47:             {
   48:                 "uir_version": "1.0",
   49:                 "doc_id": case["case_id"],
   50:                 "metadata": case.get("metadata", {}),
   51:                 "blocks": [],
   52:             }
   53:         ),
   54:         transformed_fields=case.get("transformed_fields", {}),
   55:         template=template,
   56:         system_context={"doc_id": case["case_id"]},
   57:     )
   58:     issues = [
   59:         {
   60:             "stage": issue.stage,
   61:             "path": issue.path,
   62:             "error_code": issue.error_code,
   63:         }
   64:         for issue in result.report.issues
   65:     ]
   66:     expected_issue = case.get("expected_issue")
   67:     issue_localized = expected_issue is None or expected_issue in issues
   68:     passed = (
   69:         result.passed is case["expected_passed"]
   70:         and result.document_metadata == case["expected_document_metadata"]
   71:         and issue_localized
   72:     )
   73:     return {
   74:         "case_id": case["case_id"],
   75:         "category": case["category"],
   76:         "passed": passed,
   77:         "expected_passed": case["expected_passed"],
   78:         "actual_passed": result.passed,
   79:         "expected_document_metadata": case["expected_document_metadata"],
   80:         "actual_document_metadata": result.document_metadata,
   81:         "expected_issue": expected_issue,
   82:         "actual_issues": issues,
   83:         "issue_localized": issue_localized,
   84:     }
   85: 
   86: 
   87: def build_report(fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
   88:     fixture = load_fixture(fixture_path)
   89:     cases = [evaluate_case(case) for case in fixture["cases"]]
   90:     effectiveness = [case for case in cases if case["category"] == "effectiveness"]
   91:     localization = [case for case in cases if case["category"] == "localization"]
   92:     effectiveness_rate = sum(case["passed"] for case in effectiveness) / len(effectiveness)
   93:     localization_rate = sum(case["issue_localized"] for case in localization) / len(
   94:         localization
   95:     )
   96:     return build_case_report(
   97:         fixture_path=fixture_path,
   98:         fixture=fixture,
   99:         cases=cases,
  100:         metrics={
  101:             "metadata_template_effective": effectiveness_rate == 1.0,
  102:             "metadata_template_effectiveness_rate": effectiveness_rate,
  103:             "metadata_required_localization_rate": localization_rate,
  104:         },
  105:         reproduction_command="python scripts/eval_topic5_metadata_contract.py",
  106:         claim_boundary=(
  107:             "Measures declared metadata-template rendering and exact issue localization; "
  108:             "it does not measure upstream extraction quality."
  109:         ),
  110:     )
  111: 
  112: 
  113: def main() -> None:
  114:     parser = argparse.ArgumentParser(description=__doc__)
  115:     parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
  116:     parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
  117:     args = parser.parse_args()
  118:     write_json_report(build_report(args.fixture), args.output)
  119: 
  120: 
  121: if __name__ == "__main__":
  122:     main()

## Full file: scripts/eval_topic5_summary_faithfulness.py
    1: """Evaluate Topic 5 document-summary faithfulness from declared source cases."""
    2: 
    3: from __future__ import annotations
    4: 
    5: import argparse
    6: import sys
    7: from pathlib import Path
    8: from typing import Any
    9: 
   10: 
   11: ROOT = Path(__file__).resolve().parents[1]
   12: BACKEND = ROOT / "backend"
   13: for import_path in (ROOT, BACKEND):
   14:     if str(import_path) not in sys.path:
   15:         sys.path.insert(0, str(import_path))
   16: 
   17: from app.schemas.canonical import CanonicalModel  # noqa: E402
   18: from app.schemas.content_organization import SummaryConfig  # noqa: E402
   19: from app.services.document_summary_service import DocumentSummaryService  # noqa: E402
   20: from scripts.topic5_eval_common import (  # noqa: E402
   21:     build_case_report,
   22:     load_case_fixture,
   23:     write_json_report,
   24: )
   25: 
   26: 
   27: DEFAULT_FIXTURE = ROOT / "eval" / "topic5_summary_faithfulness" / "v2" / "cases.json"
   28: DEFAULT_OUTPUT = ROOT / "reports" / "topic5_batch_2" / "summary_faithfulness.json"
   29: DATASET_ID = "topic5_summary_faithfulness"
   30: 
   31: 
   32: def load_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
   33:     return load_case_fixture(path, dataset_id=DATASET_ID)
   34: 
   35: 
   36: def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
   37:     canonical = CanonicalModel.model_validate(
   38:         {
   39:             "canonical_version": "1.0",
   40:             "task_id": f"summary-{case['case_id']}",
   41:             "doc_id": case["case_id"],
   42:             "schema_id": "summary_eval",
   43:             "blocks": case["blocks"],
   44:         }
   45:     )
   46:     summary = DocumentSummaryService().build(
   47:         canonical=canonical,
   48:         chunks=case.get("chunks", []),
   49:         config=SummaryConfig.model_validate(case.get("config", {})),
   50:     )
   51:     if summary is None:
   52:         return {
   53:             "case_id": case["case_id"],
   54:             "passed": False,
   55:             "faithful": False,
   56:             "source_coverage": 0.0,
   57:             "new_fact_violations": 1,
   58:             "actual_summary": None,
   59:         }
   60: 
   61:     blocks = {block.block_id: block.text for block in canonical.blocks}
   62:     new_fact_violations = sum(
   63:         trace.source_block_id not in blocks
   64:         or trace.source_text_span not in blocks.get(trace.source_block_id, "")
   65:         or trace.summary_sentence != trace.source_text_span
   66:         for trace in summary.sentence_traces
   67:     )
   68:     faithful = summary.faithfulness_passed and new_fact_violations == 0
   69:     expected_blocks = set(case.get("expected_source_block_ids", []))
   70:     expected_chunks = set(case.get("expected_source_chunk_ids", []))
   71:     expected_sources = len(expected_blocks) + len(expected_chunks)
   72:     covered_sources = len(expected_blocks.intersection(summary.source_block_ids)) + len(
   73:         expected_chunks.intersection(summary.source_chunk_ids)
   74:     )
   75:     source_coverage = 1.0 if expected_sources == 0 else covered_sources / expected_sources
   76:     passed = (
   77:         summary.text == case["expected_text"]
   78:         and summary.source_block_ids == case.get("expected_source_block_ids", [])
   79:         and summary.source_chunk_ids == case.get("expected_source_chunk_ids", [])
   80:         and faithful
   81:         and source_coverage == 1.0
   82:     )
   83:     return {
   84:         "case_id": case["case_id"],
   85:         "passed": passed,
   86:         "faithful": faithful,
   87:         "source_coverage": source_coverage,
   88:         "new_fact_violations": new_fact_violations,
   89:         "expected_text": case["expected_text"],
   90:         "actual_summary": summary.model_dump(mode="json"),
   91:     }
   92: 
   93: 
   94: def build_report(fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
   95:     fixture = load_fixture(fixture_path)
   96:     cases = [evaluate_case(case) for case in fixture["cases"]]
   97:     total = len(cases)
   98:     return build_case_report(
   99:         fixture_path=fixture_path,
  100:         fixture=fixture,
  101:         cases=cases,
  102:         metrics={
  103:             "document_summary_faithfulness": (
  104:                 sum(case["faithful"] for case in cases) / total
  105:             ),
  106:             "document_summary_source_coverage": (
  107:                 sum(case["source_coverage"] for case in cases) / total
  108:             ),
  109:             "document_summary_new_fact_violations": sum(
  110:                 case["new_fact_violations"] for case in cases
  111:             ),
  112:         },
  113:         reproduction_command="python scripts/eval_topic5_summary_faithfulness.py",
  114:         claim_boundary=(
  115:             "Measures extractive summary traces, declared source coverage, and facts absent "
  116:             "from those traces; it does not grade abstractiveness or writing quality."
  117:         ),
  118:     )
  119: 
  120: 
  121: def main() -> None:
  122:     parser = argparse.ArgumentParser(description=__doc__)
  123:     parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
  124:     parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
  125:     args = parser.parse_args()
  126:     write_json_report(build_report(args.fixture), args.output)
  127: 
  128: 
  129: if __name__ == "__main__":
  130:     main()

## Full file: scripts/eval_topic5_artifact_consistency.py
    1: """Evaluate Topic 5 artifact consistency and declared tampering cases."""
    2: 
    3: from __future__ import annotations
    4: 
    5: import argparse
    6: import copy
    7: import re
    8: import sys
    9: from pathlib import Path
   10: from typing import Any
   11: 
   12: 
   13: ROOT = Path(__file__).resolve().parents[1]
   14: BACKEND = ROOT / "backend"
   15: for import_path in (ROOT, BACKEND):
   16:     if str(import_path) not in sys.path:
   17:         sys.path.insert(0, str(import_path))
   18: 
   19: from app.schemas.canonical import CanonicalModel  # noqa: E402
   20: from app.schemas.document_summary import DocumentSummary  # noqa: E402
   21: from app.services.artifact_consistency_service import ArtifactConsistencyService  # noqa: E402
   22: from app.services.render_service import RenderService  # noqa: E402
   23: from scripts.topic5_eval_common import (  # noqa: E402
   24:     build_case_report,
   25:     load_case_fixture,
   26:     write_json_report,
   27: )
   28: 
   29: 
   30: DEFAULT_FIXTURE = ROOT / "eval" / "topic5_artifact_consistency" / "v2" / "cases.json"
   31: DEFAULT_OUTPUT = ROOT / "reports" / "topic5_batch_2" / "artifact_consistency.json"
   32: DATASET_ID = "topic5_artifact_consistency"
   33: 
   34: 
   35: def load_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
   36:     fixture = load_case_fixture(path, dataset_id=DATASET_ID)
   37:     if not isinstance(fixture.get("base"), dict):
   38:         raise ValueError("artifact-consistency fixture requires a base artifact")
   39:     return fixture
   40: 
   41: 
   42: def evaluate_case(case: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
   43:     summary = DocumentSummary.model_validate(base["document_summary"])
   44:     canonical_payload = copy.deepcopy(base["canonical"])
   45:     canonical_payload.setdefault("doc_meta", {})["document_summary"] = summary.model_dump(
   46:         mode="json"
   47:     )
   48:     canonical = CanonicalModel.model_validate(canonical_payload)
   49:     rendered = RenderService().render(canonical)
   50:     structured = copy.deepcopy(rendered.structured_json)
   51:     markdown = rendered.markdown
   52:     chunks = copy.deepcopy(base["chunks"])
   53: 
   54:     mutation = case["mutation"]
   55:     if mutation == "structured_field_change":
   56:         structured["data"][case["field_id"]] = case["replacement"]
   57:     elif mutation == "markdown_block_omission":
   58:         block_id = re.escape(case["block_id"])
   59:         markdown = re.sub(
   60:             rf'<!-- topic5:block:start id="{block_id}".*?'
   61:             rf'<!-- topic5:block:end id="{block_id}" -->\n?',
   62:             "",
   63:             markdown,
   64:             flags=re.DOTALL,
   65:         )
   66:     elif mutation == "chunk_unknown_source":
   67:         chunks[case["chunk_index"]]["source_block_ids"] = ["unknown"]
   68:     elif mutation != "none":
   69:         raise ValueError(f"unsupported artifact mutation: {mutation}")
   70: 
   71:     report = ArtifactConsistencyService().verify(
   72:         canonical=canonical,
   73:         structured_json=structured,
   74:         markdown=markdown,
   75:         chunks=chunks,
   76:         document_summary=summary,
   77:     )
   78:     error_codes = [issue.error_code for issue in report.errors]
   79:     expected_code = case.get("expected_error_code")
   80:     detected = report.passed is False and (
   81:         expected_code is None or expected_code in error_codes
   82:     )
   83:     passed = report.passed is case["expected_report_passed"] and (
   84:         expected_code is None or expected_code in error_codes
   85:     )
   86:     return {
   87:         "case_id": case["case_id"],
   88:         "category": case["category"],
   89:         "passed": passed,
   90:         "expected_report_passed": case["expected_report_passed"],
   91:         "actual_report_passed": report.passed,
   92:         "error_codes": error_codes,
   93:         "tampering_detected": detected if case["category"] == "tampering" else None,
   94:         "block_coverage": report.block_coverage,
   95:         "chunk_source_coverage": report.chunk_source_coverage,
   96:     }
   97: 
   98: 
   99: def build_report(fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
  100:     fixture = load_fixture(fixture_path)
  101:     cases = [evaluate_case(case, fixture["base"]) for case in fixture["cases"]]
  102:     baselines = [case for case in cases if case["category"] == "baseline"]
  103:     tampering = [case for case in cases if case["category"] == "tampering"]
  104:     return build_case_report(
  105:         fixture_path=fixture_path,
  106:         fixture=fixture,
  107:         cases=cases,
  108:         metrics={
  109:             "artifact_consistency_pass_rate": (
  110:                 sum(case["actual_report_passed"] for case in baselines) / len(baselines)
  111:             ),
  112:             "markdown_block_coverage": (
  113:                 sum(case["block_coverage"] for case in baselines) / len(baselines)
  114:             ),
  115:             "chunk_source_coverage": (
  116:                 sum(case["chunk_source_coverage"] for case in baselines) / len(baselines)
  117:             ),
  118:             "tampering_detection_rate": (
  119:                 sum(case["tampering_detected"] for case in tampering) / len(tampering)
  120:             ),
  121:         },
  122:         reproduction_command="python scripts/eval_topic5_artifact_consistency.py",
  123:         claim_boundary=(
  124:             "Measures declared JSON/Markdown/chunk consistency and deterministic tampering "
  125:             "detection; it does not establish cryptographic package authenticity."
  126:         ),
  127:     )
  128: 
  129: 
  130: def main() -> None:
  131:     parser = argparse.ArgumentParser(description=__doc__)
  132:     parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
  133:     parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
  134:     args = parser.parse_args()
  135:     write_json_report(build_report(args.fixture), args.output)
  136: 
  137: 
  138: if __name__ == "__main__":
  139:     main()

## Full file: scripts/eval_topic5_entity_passthrough.py
    1: """Evaluate Topic 5 upstream entity passthrough with declared chunk expectations."""
    2: 
    3: from __future__ import annotations
    4: 
    5: import argparse
    6: import sys
    7: from collections import Counter
    8: from pathlib import Path
    9: from typing import Any
   10: 
   11: 
   12: ROOT = Path(__file__).resolve().parents[1]
   13: BACKEND = ROOT / "backend"
   14: for import_path in (ROOT, BACKEND):
   15:     if str(import_path) not in sys.path:
   16:         sys.path.insert(0, str(import_path))
   17: 
   18: from app.schemas.canonical import CanonicalModel  # noqa: E402
   19: from app.schemas.reports import MappingReport  # noqa: E402
   20: from app.schemas.target_schema import TargetSchema  # noqa: E402
   21: from app.services.chunk_organizer_service import ChunkOrganizerService  # noqa: E402
   22: from scripts.topic5_eval_common import (  # noqa: E402
   23:     build_case_report,
   24:     load_case_fixture,
   25:     write_json_report,
   26: )
   27: 
   28: 
   29: DEFAULT_FIXTURE = ROOT / "eval" / "topic5_entity_passthrough" / "v2" / "cases.json"
   30: DEFAULT_OUTPUT = ROOT / "reports" / "topic5_batch_2" / "entity_passthrough.json"
   31: DATASET_ID = "topic5_entity_passthrough"
   32: 
   33: 
   34: def load_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
   35:     return load_case_fixture(path, dataset_id=DATASET_ID)
   36: 
   37: 
   38: def _identity(entity: dict[str, Any]) -> str:
   39:     normalized_id = entity.get("normalized_id")
   40:     if normalized_id:
   41:         return str(normalized_id)
   42:     return f"mention:{entity.get('mention')}:{entity.get('link_status')}"
   43: 
   44: 
   45: def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
   46:     canonical = CanonicalModel.model_validate(
   47:         {
   48:             "canonical_version": "1.0",
   49:             "task_id": f"entity-{case['case_id']}",
   50:             "doc_id": case["case_id"],
   51:             "schema_id": "entity_eval",
   52:             "doc_meta": {"entities": case["entities"]},
   53:             "blocks": case["blocks"],
   54:         }
   55:     )
   56:     schema = TargetSchema.model_validate(
   57:         {
   58:             "schema_id": "entity_eval",
   59:             "name": "Entity Evaluation",
   60:             "version": "1.0.0",
   61:             "fields": [
   62:                 {
   63:                     "field_id": "title",
   64:                     "name": "title",
   65:                     "display_name": "Title",
   66:                     "type": "string",
   67:                     "required": False,
   68:                 }
   69:             ],
   70:         }
   71:     )
   72:     mapping = MappingReport(
   73:         task_id=f"entity-{case['case_id']}",
   74:         schema_id="entity_eval",
   75:         summary={},
   76:         mappings=[],
   77:         unmapped=[],
   78:         review_required_items=[],
   79:     )
   80:     chunks, _report = ChunkOrganizerService().organize_chunks(
   81:         chunks=case["chunks"],
   82:         canonical_model=canonical,
   83:         schema=schema,
   84:         mapping_report=mapping,
   85:         validation_report=None,
   86:         task_id=f"entity-{case['case_id']}",
   87:         doc_id=case["case_id"],
   88:         schema_id="entity_eval",
   89:         template_id="entity-eval-v2",
   90:         options=None,
   91:     )
   92:     actual = [
   93:         [_identity(tag) for tag in chunk.get("entity_tags", [])] for chunk in chunks
   94:     ]
   95:     expected = case["expected_entity_keys_by_chunk"]
   96:     matched_count = sum(
   97:         sum((Counter(expected_keys) & Counter(actual_keys)).values())
   98:         for expected_keys, actual_keys in zip(expected, actual, strict=True)
   99:     )
  100:     expected_count = sum(len(keys) for keys in expected)
  101:     upstream_ids = {
  102:         str(entity["normalized_id"])
  103:         for entity in case["entities"]
  104:         if entity.get("normalized_id")
  105:     }
  106:     actual_ids = {
  107:         str(tag["normalized_id"])
  108:         for chunk in chunks
  109:         for tag in chunk.get("entity_tags", [])
  110:         if tag.get("normalized_id")
  111:     }
  112:     invented_ids = sorted(actual_ids - upstream_ids)
  113:     return {
  114:         "case_id": case["case_id"],
  115:         "passed": actual == expected and not invented_ids,
  116:         "expected_entity_keys_by_chunk": expected,
  117:         "actual_entity_keys_by_chunk": actual,
  118:         "matched_count": matched_count,
  119:         "expected_count": expected_count,
  120:         "invented_entity_ids": invented_ids,
  121:     }
  122: 
  123: 
  124: def build_report(fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
  125:     fixture = load_fixture(fixture_path)
  126:     cases = [evaluate_case(case) for case in fixture["cases"]]
  127:     expected_count = sum(case["expected_count"] for case in cases)
  128:     matched_count = sum(case["matched_count"] for case in cases)
  129:     invented_count = sum(len(case["invented_entity_ids"]) for case in cases)
  130:     return build_case_report(
  131:         fixture_path=fixture_path,
  132:         fixture=fixture,
  133:         cases=cases,
  134:         metrics={
  135:             "entity_passthrough_coverage": (
  136:                 1.0 if expected_count == 0 else matched_count / expected_count
  137:             ),
  138:             "invented_entity_id_count": invented_count,
  139:         },
  140:         reproduction_command="python scripts/eval_topic5_entity_passthrough.py",
  141:         claim_boundary=(
  142:             "Measures preservation of declared upstream entity identities in relevant "
  143:             "chunks; it does not evaluate entity recognition or linking accuracy."
  144:         ),
  145:     )
  146: 
  147: 
  148: def main() -> None:
  149:     parser = argparse.ArgumentParser(description=__doc__)
  150:     parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
  151:     parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
  152:     args = parser.parse_args()
  153:     write_json_report(build_report(args.fixture), args.output)
  154: 
  155: 
  156: if __name__ == "__main__":
  157:     main()

## Full file: scripts/eval_topic5_topic11_adapter.py
    1: """Evaluate offline Topic 11 adapter fallback, safety, and legacy compatibility."""
    2: 
    3: from __future__ import annotations
    4: 
    5: import argparse
    6: import json
    7: import sys
    8: from pathlib import Path
    9: from typing import Any
   10: 
   11: import httpx
   12: 
   13: 
   14: ROOT = Path(__file__).resolve().parents[1]
   15: BACKEND = ROOT / "backend"
   16: for import_path in (ROOT, BACKEND):
   17:     if str(import_path) not in sys.path:
   18:         sys.path.insert(0, str(import_path))
   19: 
   20: from app.config import Settings  # noqa: E402
   21: from app.schemas.canonical import CanonicalModel  # noqa: E402
   22: from app.schemas.chunk_provider import ChunkProviderResponse  # noqa: E402
   23: from app.schemas.content_organization import ContentOrganizationOptions  # noqa: E402
   24: from app.services.chunk_providers.base import (  # noqa: E402
   25:     ChunkProviderError,
   26:     ChunkProviderInvocation,
   27: )
   28: from app.services.chunk_providers.resolver import ChunkProviderResolver  # noqa: E402
   29: from app.services.chunk_providers.topic11_http import Topic11HttpChunkProvider  # noqa: E402
   30: from scripts.topic5_eval_common import (  # noqa: E402
   31:     build_case_report,
   32:     load_case_fixture,
   33:     write_json_report,
   34: )
   35: 
   36: 
   37: DEFAULT_FIXTURE = ROOT / "eval" / "topic5_topic11_adapter" / "v2" / "cases.json"
   38: DEFAULT_OUTPUT = ROOT / "reports" / "topic5_batch_2" / "topic11_adapter.json"
   39: DATASET_ID = "topic5_topic11_adapter"
   40: 
   41: 
   42: class FixtureProvider:
   43:     def __init__(
   44:         self,
   45:         *,
   46:         response: ChunkProviderResponse | None = None,
   47:         error_code: str | None = None,
   48:     ) -> None:
   49:         self.response = response
   50:         self.error_code = error_code
   51: 
   52:     def provide(self, _request) -> ChunkProviderInvocation:
   53:         if self.error_code:
   54:             raise ChunkProviderError(self.error_code)
   55:         if self.response is None:
   56:             raise AssertionError("fixture provider requires a response or error")
   57:         return ChunkProviderInvocation(response=self.response, latency_ms=1)
   58: 
   59: 
   60: def load_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
   61:     fixture = load_case_fixture(path, dataset_id=DATASET_ID)
   62:     if not isinstance(fixture.get("base"), dict):
   63:         raise ValueError("Topic 11 fixture requires base canonical and legacy chunks")
   64:     return fixture
   65: 
   66: 
   67: def _options() -> ContentOrganizationOptions:
   68:     return ContentOrganizationOptions.model_validate(
   69:         {
   70:             "provider": "topic11",
   71:             "fallback_to_internal": True,
   72:             "strict_provider": False,
   73:             "chunk_strategy": "source_block_aware",
   74:             "target_tokens": 128,
   75:             "min_tokens": 1,
   76:             "max_tokens": 256,
   77:             "overlap_tokens": 0,
   78:         }
   79:     )
   80: 
   81: 
   82: def _response(chunks: list[dict[str, Any]]) -> ChunkProviderResponse:
   83:     return ChunkProviderResponse.model_validate(
   84:         {
   85:             "contract_version": "1.0",
   86:             "provider": "topic11",
   87:             "provider_version": "fixture-v2",
   88:             "chunks": chunks,
   89:             "warnings": [],
   90:             "trace": {},
   91:         }
   92:     )
   93: 
   94: 
   95: def evaluate_case(case: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
   96:     canonical = CanonicalModel.model_validate(base["canonical"])
   97:     legacy_chunks = base["legacy_chunks"]
   98:     secret = str(case.get("secret") or "")
   99:     client: httpx.Client | None = None
  100: 
  101:     if case["category"] == "legacy":
  102:         resolver = ChunkProviderResolver(settings=Settings(offline_mode=True))
  103:         result = resolver.resolve(
  104:             canonical=canonical,
  105:             options=None,
  106:             legacy_chunks=legacy_chunks,
  107:         )
  108:         legacy_compatible = result.chunks == legacy_chunks
  109:         return {
  110:             "case_id": case["case_id"],
  111:             "category": case["category"],
  112:             "passed": legacy_compatible,
  113:             "legacy_compatible": legacy_compatible,
  114:             "fallback_succeeded": None,
  115:             "invalid_output_accepted": False,
  116:             "secret_leaked": False,
  117:             "trace": result.trace.model_dump(mode="json"),
  118:         }
  119: 
  120:     if case["category"] == "secret":
  121:         settings = Settings(
  122:             topic11_base_url="https://topic11.invalid",
  123:             topic11_api_key=secret,
  124:         )
  125: 
  126:         def timeout_handler(_request: httpx.Request) -> httpx.Response:
  127:             raise httpx.ReadTimeout(secret)
  128: 
  129:         client = httpx.Client(transport=httpx.MockTransport(timeout_handler))
  130:         provider = Topic11HttpChunkProvider(settings, client=client)
  131:     elif case["category"] == "invalid":
  132:         settings = Settings()
  133:         provider = FixtureProvider(response=_response(case["chunks"]))
  134:     else:
  135:         settings = Settings()
  136:         provider = FixtureProvider(error_code=case["error_code"])
  137: 
  138:     try:
  139:         result = ChunkProviderResolver(
  140:             settings=settings,
  141:             external_provider=provider,
  142:         ).resolve(
  143:             canonical=canonical,
  144:             options=_options(),
  145:             legacy_chunks=legacy_chunks,
  146:         )
  147:     finally:
  148:         if client is not None:
  149:             client.close()
  150: 
  151:     trace = result.trace.model_dump(mode="json")
  152:     fallback_succeeded = (
  153:         trace["fallback_used"] is True
  154:         and trace["used_provider"] == "internal"
  155:         and trace["fallback_reason"] == case["expected_fallback_reason"]
  156:     )
  157:     invalid_output_accepted = (
  158:         case["category"] == "invalid" and trace["used_provider"] == "topic11"
  159:     )
  160:     serialized = json.dumps(
  161:         {"trace": trace, "chunks": result.chunks}, ensure_ascii=False, sort_keys=True
  162:     )
  163:     secret_leaked = bool(secret and secret in serialized)
  164:     return {
  165:         "case_id": case["case_id"],
  166:         "category": case["category"],
  167:         "passed": fallback_succeeded and not invalid_output_accepted and not secret_leaked,
  168:         "legacy_compatible": None,
  169:         "fallback_succeeded": fallback_succeeded,
  170:         "invalid_output_accepted": invalid_output_accepted,
  171:         "secret_leaked": secret_leaked,
  172:         "trace": trace,
  173:     }
  174: 
  175: 
  176: def build_report(fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
  177:     fixture = load_fixture(fixture_path)
  178:     cases = [evaluate_case(case, fixture["base"]) for case in fixture["cases"]]
  179:     fallback_cases = [case for case in cases if case["category"] != "legacy"]
  180:     legacy_cases = [case for case in cases if case["category"] == "legacy"]
  181:     legacy_rate = sum(case["legacy_compatible"] for case in legacy_cases) / len(
  182:         legacy_cases
  183:     )
  184:     return build_case_report(
  185:         fixture_path=fixture_path,
  186:         fixture=fixture,
  187:         cases=cases,
  188:         metrics={
  189:             "topic11_fallback_success_rate": (
  190:                 sum(case["fallback_succeeded"] for case in fallback_cases)
  191:                 / len(fallback_cases)
  192:             ),
  193:             "topic11_invalid_output_acceptance_count": sum(
  194:                 case["invalid_output_accepted"] for case in cases
  195:             ),
  196:             "secret_leak_count": sum(case["secret_leaked"] for case in cases),
  197:             "legacy_compatibility_rate": legacy_rate,
  198:             "legacy_request_regression": int(legacy_rate != 1.0),
  199:             "legacy_package_regression": int(legacy_rate != 1.0),
  200:         },
  201:         reproduction_command="python scripts/eval_topic5_topic11_adapter.py",
  202:         claim_boundary=(
  203:             "Measures deterministic offline Topic 11 adapter contracts with fixture and "
  204:             "mock transports; it makes no live-service availability claim."
  205:         ),
  206:     )
  207: 
  208: 
  209: def main() -> None:
  210:     parser = argparse.ArgumentParser(description=__doc__)
  211:     parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
  212:     parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
  213:     args = parser.parse_args()
  214:     write_json_report(build_report(args.fixture), args.output)
  215: 
  216: 
  217: if __name__ == "__main__":
  218:     main()

## Full file: eval/topic5_metadata_contract/v2/cases.json
    1: {
    2:   "dataset_id": "topic5_metadata_contract",
    3:   "version": "2.0.0",
    4:   "cases": [
    5:     {
    6:       "case_id": "metadata_source_value",
    7:       "category": "effectiveness",
    8:       "metadata": {"language": "zh-CN"},
    9:       "metadata_fields": [
   10:         {"field_id": "language", "type": "string"}
   11:       ],
   12:       "expected_passed": true,
   13:       "expected_document_metadata": {"language": "zh-CN"}
   14:     },
   15:     {
   16:       "case_id": "metadata_default_value",
   17:       "category": "effectiveness",
   18:       "metadata": {},
   19:       "metadata_fields": [
   20:         {"field_id": "language", "type": "string", "default": "en-US"}
   21:       ],
   22:       "expected_passed": true,
   23:       "expected_document_metadata": {"language": "en-US"}
   24:     },
   25:     {
   26:       "case_id": "metadata_required_missing",
   27:       "category": "localization",
   28:       "metadata": {},
   29:       "metadata_fields": [
   30:         {"field_id": "classification", "type": "string", "required": true}
   31:       ],
   32:       "expected_passed": false,
   33:       "expected_document_metadata": {},
   34:       "expected_issue": {
   35:         "stage": "metadata_template",
   36:         "path": "document_metadata.classification",
   37:         "error_code": "metadata_required_missing"
   38:       }
   39:     },
   40:     {
   41:       "case_id": "metadata_type_mismatch",
   42:       "category": "localization",
   43:       "metadata": {"retention_years": "seven"},
   44:       "metadata_fields": [
   45:         {"field_id": "retention_years", "type": "integer"}
   46:       ],
   47:       "expected_passed": false,
   48:       "expected_document_metadata": {},
   49:       "expected_issue": {
   50:         "stage": "metadata_template",
   51:         "path": "document_metadata.retention_years",
   52:         "error_code": "metadata_type_mismatch"
   53:       }
   54:     }
   55:   ]
   56: }

## Full file: eval/topic5_summary_faithfulness/v2/cases.json
    1: {
    2:   "dataset_id": "topic5_summary_faithfulness",
    3:   "version": "2.0.0",
    4:   "cases": [
    5:     {
    6:       "case_id": "section_summary",
    7:       "blocks": [
    8:         {"block_id": "h1", "type": "heading", "level": 1, "text": "Overview", "source_blocks": ["h1"]},
    9:         {"block_id": "p1", "type": "paragraph", "text": "First overview fact. Second overview fact.", "source_blocks": ["p1"]},
   10:         {"block_id": "h2", "type": "heading", "level": 1, "text": "Details", "source_blocks": ["h2"]},
   11:         {"block_id": "p2", "type": "paragraph", "text": "First detail fact. Second detail fact.", "source_blocks": ["p2"]}
   12:       ],
   13:       "chunks": [
   14:         {"chunk_id": "c1", "source_block_ids": ["p1"]},
   15:         {"chunk_id": "c2", "source_block_ids": ["p2"]}
   16:       ],
   17:       "config": {"document_max_sentences": 5, "document_max_chars": 500},
   18:       "expected_text": "First overview fact.\nFirst detail fact.",
   19:       "expected_source_block_ids": ["p1", "p2"],
   20:       "expected_source_chunk_ids": ["c1", "c2"]
   21:     },
   22:     {
   23:       "case_id": "source_order_summary",
   24:       "blocks": [
   25:         {"block_id": "p1", "type": "paragraph", "text": "One. Two.", "source_blocks": ["p1"]},
   26:         {"block_id": "p2", "type": "paragraph", "text": "Three.", "source_blocks": ["p2"]}
   27:       ],
   28:       "chunks": [
   29:         {"chunk_id": "c1", "source_block_ids": ["p1"]},
   30:         {"chunk_id": "c2", "source_block_ids": ["p2"]}
   31:       ],
   32:       "config": {"document_max_sentences": 3, "document_max_chars": 500},
   33:       "expected_text": "One.\nTwo.\nThree.",
   34:       "expected_source_block_ids": ["p1", "p2"],
   35:       "expected_source_chunk_ids": ["c1", "c2"]
   36:     },
   37:     {
   38:       "case_id": "empty_document",
   39:       "blocks": [],
   40:       "chunks": [],
   41:       "config": {},
   42:       "expected_text": "",
   43:       "expected_source_block_ids": [],
   44:       "expected_source_chunk_ids": []
   45:     }
   46:   ]
   47: }

## Full file: eval/topic5_artifact_consistency/v2/cases.json
    1: {
    2:   "dataset_id": "topic5_artifact_consistency",
    3:   "version": "2.0.0",
    4:   "base": {
    5:     "canonical": {
    6:       "canonical_version": "1.0",
    7:       "task_id": "artifact-eval",
    8:       "doc_id": "artifact-eval",
    9:       "schema_id": "artifact_eval",
   10:       "doc_meta": {
   11:         "document_metadata": {"language": "en-US"},
   12:         "entities": [
   13:           {
   14:             "mention": "OpenAI",
   15:             "canonical_name": "OpenAI",
   16:             "entity_type": "organization",
   17:             "normalized_id": "org:openai",
   18:             "link_status": "linked",
   19:             "confidence": 1.0,
   20:             "source_block_ids": ["b1"],
   21:             "source_agent": "topic7",
   22:             "evidence": {}
   23:           }
   24:         ]
   25:       },
   26:       "fields": {
   27:         "title": {"value": "Notice", "type": "string", "source_blocks": ["b1"]}
   28:       },
   29:       "blocks": [
   30:         {"block_id": "b1", "type": "paragraph", "text": "OpenAI published the notice.", "source_blocks": ["b1"]},
   31:         {"block_id": "b2", "type": "table", "text": "Field: Value", "source_blocks": ["b2"]}
   32:       ]
   33:     },
   34:     "document_summary": {
   35:       "text": "OpenAI published the notice.",
   36:       "mode": "extractive",
   37:       "source_block_ids": ["b1"],
   38:       "source_chunk_ids": ["c1"],
   39:       "sentence_traces": [
   40:         {
   41:           "summary_sentence": "OpenAI published the notice.",
   42:           "source_block_id": "b1",
   43:           "source_text_span": "OpenAI published the notice."
   44:         }
   45:       ],
   46:       "char_count": 28,
   47:       "faithfulness_passed": true,
   48:       "warnings": []
   49:     },
   50:     "chunks": [
   51:       {
   52:         "chunk_id": "c1",
   53:         "parent_chunk_id": null,
   54:         "index": 0,
   55:         "chunk_index": 0,
   56:         "text": "OpenAI published the notice.",
   57:         "source_block_ids": ["b1"],
   58:         "source_links": [{"block_id": "b1", "source_path": "blocks[0]"}],
   59:         "entity_tags": [
   60:           {"mention": "OpenAI", "text": "OpenAI", "normalized_id": "org:openai", "source_block_ids": ["b1"], "link_status": "linked"}
   61:         ]
   62:       },
   63:       {
   64:         "chunk_id": "c2",
   65:         "parent_chunk_id": null,
   66:         "index": 1,
   67:         "chunk_index": 1,
   68:         "text": "Field: Value",
   69:         "source_block_ids": ["b2"],
   70:         "source_links": [{"block_id": "b2", "source_path": "blocks[1]"}],
   71:         "entity_tags": []
   72:       }
   73:     ]
   74:   },
   75:   "cases": [
   76:     {
   77:       "case_id": "consistent_artifacts",
   78:       "category": "baseline",
   79:       "mutation": "none",
   80:       "expected_report_passed": true
   81:     },
   82:     {
   83:       "case_id": "structured_field_tampering",
   84:       "category": "tampering",
   85:       "mutation": "structured_field_change",
   86:       "field_id": "title",
   87:       "replacement": "Changed",
   88:       "expected_report_passed": false,
   89:       "expected_error_code": "json_field_mismatch"
   90:     },
   91:     {
   92:       "case_id": "markdown_block_tampering",
   93:       "category": "tampering",
   94:       "mutation": "markdown_block_omission",
   95:       "block_id": "b2",
   96:       "expected_report_passed": false,
   97:       "expected_error_code": "markdown_block_missing"
   98:     },
   99:     {
  100:       "case_id": "chunk_source_tampering",
  101:       "category": "tampering",
  102:       "mutation": "chunk_unknown_source",
  103:       "chunk_index": 0,
  104:       "expected_report_passed": false,
  105:       "expected_error_code": "chunk_source_unknown"
  106:     }
  107:   ]
  108: }

## Full file: eval/topic5_entity_passthrough/v2/cases.json
    1: {
    2:   "dataset_id": "topic5_entity_passthrough",
    3:   "version": "2.0.0",
    4:   "cases": [
    5:     {
    6:       "case_id": "linked_entity_single_source",
    7:       "entities": [
    8:         {
    9:           "mention": "OpenAI",
   10:           "canonical_name": "OpenAI",
   11:           "entity_type": "organization",
   12:           "normalized_id": "org:openai",
   13:           "link_status": "linked",
   14:           "confidence": 0.99,
   15:           "source_block_ids": ["b1"],
   16:           "source_agent": "topic7"
   17:         }
   18:       ],
   19:       "blocks": [
   20:         {"block_id": "b1", "type": "paragraph", "text": "OpenAI published the notice.", "source_blocks": ["b1"]},
   21:         {"block_id": "b2", "type": "paragraph", "text": "A separate paragraph.", "source_blocks": ["b2"]}
   22:       ],
   23:       "chunks": [
   24:         {"chunk_id": "c1", "text": "OpenAI published the notice.", "source_block_ids": ["b1"]},
   25:         {"chunk_id": "c2", "text": "A separate paragraph.", "source_block_ids": ["b2"]}
   26:       ],
   27:       "expected_entity_keys_by_chunk": [["org:openai"], []]
   28:     },
   29:     {
   30:       "case_id": "linked_entity_multiple_sources",
   31:       "entities": [
   32:         {
   33:           "mention": "OpenAI",
   34:           "entity_type": "organization",
   35:           "normalized_id": "org:openai",
   36:           "link_status": "linked",
   37:           "source_block_ids": ["b1", "b2"]
   38:         }
   39:       ],
   40:       "blocks": [
   41:         {"block_id": "b1", "type": "paragraph", "text": "OpenAI published the notice.", "source_blocks": ["b1"]},
   42:         {"block_id": "b2", "type": "paragraph", "text": "The university acknowledged OpenAI.", "source_blocks": ["b2"]}
   43:       ],
   44:       "chunks": [
   45:         {"chunk_id": "c1", "text": "OpenAI published the notice.", "source_block_ids": ["b1"]},
   46:         {"chunk_id": "c2", "text": "The university acknowledged OpenAI.", "source_block_ids": ["b2"]}
   47:       ],
   48:       "expected_entity_keys_by_chunk": [["org:openai"], ["org:openai"]]
   49:     },
   50:     {
   51:       "case_id": "unlinked_entity_keeps_nil_id",
   52:       "entities": [
   53:         {
   54:           "mention": "OpenAI",
   55:           "entity_type": "organization",
   56:           "normalized_id": null,
   57:           "link_status": "unlinked",
   58:           "source_block_ids": []
   59:         }
   60:       ],
   61:       "blocks": [
   62:         {"block_id": "b1", "type": "paragraph", "text": "OpenAI published the notice.", "source_blocks": ["b1"]},
   63:         {"block_id": "b2", "type": "paragraph", "text": "A separate paragraph.", "source_blocks": ["b2"]}
   64:       ],
   65:       "chunks": [
   66:         {"chunk_id": "c1", "text": "OpenAI published the notice.", "source_block_ids": ["b1"]},
   67:         {"chunk_id": "c2", "text": "A separate paragraph.", "source_block_ids": ["b2"]}
   68:       ],
   69:       "expected_entity_keys_by_chunk": [["mention:OpenAI:unlinked"], []]
   70:     }
   71:   ]
   72: }

## Full file: eval/topic5_topic11_adapter/v2/cases.json
    1: {
    2:   "dataset_id": "topic5_topic11_adapter",
    3:   "version": "2.0.0",
    4:   "base": {
    5:     "canonical": {
    6:       "canonical_version": "1.0",
    7:       "task_id": "topic11-eval",
    8:       "doc_id": "topic11-eval",
    9:       "schema_id": "topic11_eval",
   10:       "doc_meta": {
   11:         "entities": [
   12:           {
   13:             "mention": "OpenAI",
   14:             "entity_type": "organization",
   15:             "normalized_id": "org:openai",
   16:             "link_status": "linked",
   17:             "source_block_ids": ["b1"]
   18:           }
   19:         ]
   20:       },
   21:       "blocks": [
   22:         {"block_id": "b1", "type": "paragraph", "text": "OpenAI published the notice.", "source_blocks": ["b1"]},
   23:         {"block_id": "table1", "type": "table", "text": "Field: Value", "source_blocks": ["table1"]}
   24:       ]
   25:     },
   26:     "legacy_chunks": [
   27:       {"chunk_id": "legacy-b1", "text": "OpenAI published the notice.", "source_block_ids": ["b1"]},
   28:       {"chunk_id": "legacy-table1", "text": "Field: Value", "source_block_ids": ["table1"]}
   29:     ]
   30:   },
   31:   "cases": [
   32:     {
   33:       "case_id": "timeout_fallback",
   34:       "category": "fallback",
   35:       "error_code": "topic11_timeout",
   36:       "expected_fallback_reason": "topic11_timeout"
   37:     },
   38:     {
   39:       "case_id": "http_error_fallback",
   40:       "category": "fallback",
   41:       "error_code": "topic11_http_error",
   42:       "expected_fallback_reason": "topic11_http_error"
   43:     },
   44:     {
   45:       "case_id": "unknown_source_rejected",
   46:       "category": "invalid",
   47:       "chunks": [
   48:         {"chunk_id": "bad", "text": "Unknown text", "source_block_ids": ["unknown"]}
   49:       ],
   50:       "expected_fallback_reason": "topic11_unknown_source_block"
   51:     },
   52:     {
   53:       "case_id": "invented_fact_rejected",
   54:       "category": "invalid",
   55:       "chunks": [
   56:         {"chunk_id": "bad", "text": "A fact absent from source.", "source_block_ids": ["b1"]},
   57:         {"chunk_id": "table", "text": "Field: Value", "source_block_ids": ["table1"]}
   58:       ],
   59:       "expected_fallback_reason": "topic11_chunk_text_not_derivable"
   60:     },
   61:     {
   62:       "case_id": "secret_redacted_on_timeout",
   63:       "category": "secret",
   64:       "secret": "topic11-evaluator-secret",
   65:       "expected_fallback_reason": "topic11_timeout"
   66:     },
   67:     {
   68:       "case_id": "legacy_chunks_unchanged",
   69:       "category": "legacy"
   70:     }
   71:   ]
   72: }

## Full file: scripts/check_topic5_hard_gap_batch_1_gate.py
    1: """Run the machine-readable Topic 5 hard-gap batch 1 acceptance gate."""
    2: 
    3: from __future__ import annotations
    4: 
    5: import argparse
    6: import json
    7: import subprocess
    8: import sys
    9: from datetime import UTC, datetime
   10: from pathlib import Path
   11: from typing import Any
   12: 
   13: ROOT = Path(__file__).resolve().parents[1]
   14: BACKEND = ROOT / "backend"
   15: if str(ROOT) not in sys.path:
   16:     sys.path.insert(0, str(ROOT))
   17: 
   18: from scripts.eval_topic5_field_operations import build_report as field_report  # noqa: E402
   19: from scripts.eval_topic5_artifact_consistency import (  # noqa: E402
   20:     build_report as artifact_consistency_report,
   21: )
   22: from scripts.eval_topic5_entity_passthrough import (  # noqa: E402
   23:     build_report as entity_passthrough_report,
   24: )
   25: from scripts.eval_topic5_metadata_contract import (  # noqa: E402
   26:     build_report as metadata_contract_report,
   27: )
   28: from scripts.eval_topic5_schema_localization import (  # noqa: E402
   29:     build_report as localization_report,
   30: )
   31: from scripts.eval_topic5_summary_faithfulness import (  # noqa: E402
   32:     build_report as summary_faithfulness_report,
   33: )
   34: from scripts.eval_topic5_topic11_adapter import (  # noqa: E402
   35:     build_report as topic11_adapter_report,
   36: )
   37: 
   38: DEFAULT_OUTPUT = ROOT / "docs" / "浜ゆ帴" / "evidence" / "hard_gap_batch_1" / "operations"
   39: DEFAULT_TAG_REPORT = ROOT / "docs" / "浜ゆ帴" / "evidence" / "hard_gap_batch_1" / "tags" / "content_tag_quality.json"
   40: DEFAULT_VERIFICATION = DEFAULT_OUTPUT / "verification_summary.json"
   41: 
   42: COMPONENT_TESTS = {
   43:     "metadata": [
   44:         "backend/tests/test_metadata_template_service.py",
   45:         "backend/tests/test_topic5_convert_api.py",
   46:     ],
   47:     "summary": [
   48:         "backend/tests/test_document_summary_service.py",
   49:     ],
   50:     "consistency": [
   51:         "backend/tests/test_artifact_consistency_service.py",
   52:     ],
   53:     "entity": [
   54:         "backend/tests/test_topic5_entity_passthrough.py",
   55:     ],
   56:     "topic11": [
   57:         "backend/tests/test_topic11_chunk_provider.py",
   58:     ],
   59:     "legacy": [
   60:         "backend/tests/test_package_1_1_assertion_report_compatibility.py",
   61:         "backend/tests/test_topic5_convert_api.py",
   62:     ],
   63: }
   64: EVALUATOR_BUILDERS = {
   65:     "metadata": metadata_contract_report,
   66:     "summary": summary_faithfulness_report,
   67:     "consistency": artifact_consistency_report,
   68:     "entity": entity_passthrough_report,
   69:     "topic11": topic11_adapter_report,
   70: }
   71: 
   72: 
   73: def run_component_checks() -> dict[str, dict[str, Any]]:
   74:     results: dict[str, dict[str, Any]] = {}
   75:     for name, paths in COMPONENT_TESTS.items():
   76:         command = [
   77:             sys.executable,
   78:             "-m",
   79:             "pytest",
   80:             *paths,
   81:             "-q",
   82:         ]
   83:         completed = subprocess.run(
   84:             command,
   85:             cwd=ROOT,
   86:             capture_output=True,
   87:             text=True,
   88:             check=False,
   89:         )
   90:         results[name] = {
   91:             "passed": completed.returncode == 0,
   92:             "return_code": completed.returncode,
   93:             "command": " ".join(command),
   94:             "summary": _last_nonempty_line(completed.stdout or completed.stderr),
   95:         }
   96:     return results
   97: 
   98: 
   99: def build_evaluator_reports() -> dict[str, dict[str, Any]]:
  100:     return {name: builder() for name, builder in EVALUATOR_BUILDERS.items()}
  101: 
  102: 
  103: def skipped_component_checks() -> dict[str, dict[str, Any]]:
  104:     return {
  105:         name: {
  106:             "passed": False,
  107:             "status": "skipped",
  108:             "return_code": None,
  109:             "summary": "skipped by caller",
  110:         }
  111:         for name in COMPONENT_TESTS
  112:     }
  113: 
  114: 
  115: def _validated_evaluator_reports(
  116:     reports: dict[str, dict[str, Any]] | None,
  117: ) -> dict[str, dict[str, Any]]:
  118:     reports = reports or {}
  119:     missing = sorted(EVALUATOR_BUILDERS.keys() - reports.keys())
  120:     if missing:
  121:         raise ValueError(f"missing evaluator report(s): {', '.join(missing)}")
  122:     for name in EVALUATOR_BUILDERS:
  123:         report = reports[name]
  124:         required = {
  125:             "dataset_id",
  126:             "dataset_version",
  127:             "dataset_sha256",
  128:             "commit_sha",
  129:             "case_count",
  130:             "passed_count",
  131:             "failed_cases",
  132:             "reproduction_command",
  133:             "claim_boundary",
  134:         }
  135:         absent = sorted(required - report.keys())
  136:         if absent:
  137:             raise ValueError(
  138:                 f"{name} evaluator report is missing field(s): {', '.join(absent)}"
  139:             )
  140:         case_count = report["case_count"]
  141:         passed_count = report["passed_count"]
  142:         if (
  143:             not isinstance(case_count, int)
  144:             or isinstance(case_count, bool)
  145:             or case_count <= 0
  146:             or not isinstance(passed_count, int)
  147:             or isinstance(passed_count, bool)
  148:             or not 0 <= passed_count <= case_count
  149:         ):
  150:             raise ValueError(f"{name} evaluator report has invalid case accounting")
  151:     return reports
  152: 
  153: 
  154: def evaluate_gate(
  155:     *,
  156:     operations: dict[str, Any],
  157:     localization: dict[str, Any],
  158:     tag_quality: dict[str, Any],
  159:     components: dict[str, dict[str, Any]],
  160:     evaluator_reports: dict[str, dict[str, Any]] | None = None,
  161:     verification: dict[str, Any],
  162: ) -> dict[str, Any]:
  163:     metrics = tag_quality.get("metrics", {})
  164:     reports = _validated_evaluator_reports(evaluator_reports)
  165:     metadata = reports["metadata"]
  166:     summary = reports["summary"]
  167:     consistency = reports["consistency"]
  168:     entity = reports["entity"]
  169:     topic11 = reports["topic11"]
  170: 
  171:     values = {
  172:         "metadata_template_effective": bool(metadata["metadata_template_effective"]),
  173:         "metadata_required_localization_rate": float(
  174:             metadata["metadata_required_localization_rate"]
  175:         ),
  176:         "content_tag_metric": float(metrics.get("content_tag_f1", 0.0)),
  177:         "management_tag_rule_accuracy": float(metrics.get("management_tag_f1", 0.0)),
  178:         "quality_tag_metric": float(metrics.get("quality_tag_f1", 0.0)),
  179:         "global_quality_tag_pollution_count": int(metrics.get("unknown_tag_count", -1)),
  180:         "document_summary_faithfulness": float(
  181:             summary["document_summary_faithfulness"]
  182:         ),
  183:         "document_summary_source_coverage": float(
  184:             summary["document_summary_source_coverage"]
  185:         ),
  186:         "document_summary_new_fact_violations": int(
  187:             summary["document_summary_new_fact_violations"]
  188:         ),
  189:         "artifact_consistency_pass_rate": float(
  190:             consistency["artifact_consistency_pass_rate"]
  191:         ),
  192:         "markdown_block_coverage": float(consistency["markdown_block_coverage"]),
  193:         "chunk_source_coverage": float(consistency["chunk_source_coverage"]),
  194:         "tampering_detection_rate": float(consistency["tampering_detection_rate"]),
  195:         "entity_passthrough_coverage": float(entity["entity_passthrough_coverage"]),
  196:         "invented_entity_id_count": int(entity["invented_entity_id_count"]),
  197:         "topic11_invalid_output_acceptance_count": int(
  198:             topic11["topic11_invalid_output_acceptance_count"]
  199:         ),
  200:         "topic11_fallback_success_rate": float(
  201:             topic11["topic11_fallback_success_rate"]
  202:         ),
  203:         "secret_leak_count": int(topic11["secret_leak_count"]),
  204:         "field_operation_accuracy": float(operations["field_operation_accuracy"]),
  205:         "rename_accuracy": float(operations["rename_accuracy"]),
  206:         "merge_accuracy": float(operations["merge_accuracy"]),
  207:         "split_accuracy": float(operations["split_accuracy"]),
  208:         "unsafe_operation_count": int(operations["unsafe_operation_count"]),
  209:         "schema_localization_rate": float(localization["schema_localization_rate"]),
  210:         "error_code_accuracy": float(localization["error_code_accuracy"]),
  211:         "stage_accuracy": float(localization["stage_accuracy"]),
  212:         "legacy_request_regression": int(topic11["legacy_request_regression"]),
  213:         "legacy_package_regression": int(topic11["legacy_package_regression"]),
  214:         "full_backend_tests_passed": bool(verification.get("full_backend_tests_passed")),
  215:         "ruff_clean": bool(verification.get("ruff_clean")),
  216:         "frontend_tests_passed": bool(verification.get("frontend_tests_passed")),
  217:         "openapi_export_passed": bool(verification.get("openapi_export_passed")),
  218:     }
  219:     checks = {
  220:         "metadata_template_effective": values["metadata_template_effective"] is True,
  221:         "metadata_required_localization_rate": values["metadata_required_localization_rate"] == 1.0,
  222:         "content_tag_metric": values["content_tag_metric"] >= 0.85,
  223:         "management_tag_rule_accuracy": values["management_tag_rule_accuracy"] == 1.0,
  224:         "quality_tag_metric": values["quality_tag_metric"] >= 0.85,
  225:         "global_quality_tag_pollution_count": values["global_quality_tag_pollution_count"] == 0,
  226:         "document_summary_faithfulness": values["document_summary_faithfulness"] == 1.0,
  227:         "document_summary_source_coverage": values["document_summary_source_coverage"] == 1.0,
  228:         "document_summary_new_fact_violations": values["document_summary_new_fact_violations"] == 0,
  229:         "artifact_consistency_pass_rate": values["artifact_consistency_pass_rate"] == 1.0,
  230:         "markdown_block_coverage": values["markdown_block_coverage"] == 1.0,
  231:         "chunk_source_coverage": values["chunk_source_coverage"] == 1.0,
  232:         "tampering_detection_rate": values["tampering_detection_rate"] == 1.0,
  233:         "entity_passthrough_coverage": values["entity_passthrough_coverage"] == 1.0,
  234:         "invented_entity_id_count": values["invented_entity_id_count"] == 0,
  235:         "topic11_invalid_output_acceptance_count": values["topic11_invalid_output_acceptance_count"] == 0,
  236:         "topic11_fallback_success_rate": values["topic11_fallback_success_rate"] == 1.0,
  237:         "secret_leak_count": values["secret_leak_count"] == 0,
  238:         "field_operation_accuracy": values["field_operation_accuracy"] >= 0.95,
  239:         "rename_accuracy": values["rename_accuracy"] >= 0.95,
  240:         "merge_accuracy": values["merge_accuracy"] >= 0.95,
  241:         "split_accuracy": values["split_accuracy"] >= 0.95,
  242:         "unsafe_operation_count": values["unsafe_operation_count"] == 0,
  243:         "schema_localization_rate": values["schema_localization_rate"] == 1.0,
  244:         "error_code_accuracy": values["error_code_accuracy"] == 1.0,
  245:         "stage_accuracy": values["stage_accuracy"] == 1.0,
  246:         "legacy_request_regression": values["legacy_request_regression"] == 0,
  247:         "legacy_package_regression": values["legacy_package_regression"] == 0,
  248:         "full_backend_tests_passed": values["full_backend_tests_passed"] is True,
  249:         "ruff_clean": values["ruff_clean"] is True,
  250:         "frontend_tests_passed": values["frontend_tests_passed"] is True,
  251:         "openapi_export_passed": values["openapi_export_passed"] is True,
  252:     }
  253:     failed = [name for name, result in checks.items() if not result]
  254:     return {
  255:         "generated_at": datetime.now(UTC).isoformat(),
  256:         "conclusion": "passed" if not failed else "failed",
  257:         "passed": not failed,
  258:         "values": values,
  259:         "checks": checks,
  260:         "failed_conditions": failed,
  261:         "datasets": {
  262:             "field_operations": operations["dataset_sha256"],
  263:             "schema_localization": localization["dataset_sha256"],
  264:             **{
  265:                 name: report["dataset_sha256"]
  266:                 for name, report in reports.items()
  267:             },
  268:         },
  269:         "component_checks": components,
  270:         "evaluator_reports": reports,
  271:     }
  272: 
  273: 
  274: def render_markdown(report: dict[str, Any]) -> str:
  275:     lines = [
  276:         "# Topic 5 Hard-Gap Batch 1 Gate",
  277:         "",
  278:         f"Conclusion: **{report['conclusion']}**",
  279:         "",
  280:         "| Condition | Value | Passed |",
  281:         "| --- | --- | --- |",
  282:     ]
  283:     for name, check_passed in report["checks"].items():
  284:         lines.append(f"| {name} | {report['values'][name]} | {check_passed} |")
  285:     if report["failed_conditions"]:
  286:         lines.extend(["", "Failed: " + ", ".join(report["failed_conditions"])])
  287:     return "\n".join(lines) + "\n"
  288: 
  289: 
  290: def _last_nonempty_line(value: str) -> str:
  291:     lines = [line.strip() for line in value.splitlines() if line.strip()]
  292:     return lines[-1] if lines else ""
  293: 
  294: 
  295: def main() -> None:
  296:     parser = argparse.ArgumentParser(description=__doc__)
  297:     parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
  298:     parser.add_argument("--tag-report", type=Path, default=DEFAULT_TAG_REPORT)
  299:     parser.add_argument("--verification", type=Path, default=DEFAULT_VERIFICATION)
  300:     parser.add_argument("--skip-component-tests", action="store_true")
  301:     args = parser.parse_args()
  302:     if not args.verification.is_file():
  303:         raise SystemExit(f"verification summary is missing: {args.verification}")
  304:     components = (
  305:         skipped_component_checks()
  306:         if args.skip_component_tests
  307:         else run_component_checks()
  308:     )
  309:     report = evaluate_gate(
  310:         operations=field_report(),
  311:         localization=localization_report(),
  312:         tag_quality=json.loads(args.tag_report.read_text(encoding="utf-8")),
  313:         components=components,
  314:         evaluator_reports=build_evaluator_reports(),
  315:         verification=json.loads(args.verification.read_text(encoding="utf-8")),
  316:     )
  317:     args.out_dir.mkdir(parents=True, exist_ok=True)
  318:     (args.out_dir / "hard_gap_batch_1_gate.json").write_text(
  319:         json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
  320:         encoding="utf-8",
  321:     )
  322:     (args.out_dir / "hard_gap_batch_1_gate.md").write_text(
  323:         render_markdown(report), encoding="utf-8"
  324:     )
  325:     raise SystemExit(0 if report["passed"] else 1)
  326: 
  327: 
  328: if __name__ == "__main__":
  329:     main()

## Full file: scripts/check_topic5_batch_2_acceptance_gate.py
    1: """Aggregate case-level Topic 5 Batch 2 evaluator reports into an acceptance gate."""
    2: 
    3: from __future__ import annotations
    4: 
    5: import argparse
    6: import json
    7: import sys
    8: from datetime import UTC, datetime
    9: from pathlib import Path
   10: from typing import Any
   11: 
   12: 
   13: ROOT = Path(__file__).resolve().parents[1]
   14: if str(ROOT) not in sys.path:
   15:     sys.path.insert(0, str(ROOT))
   16: 
   17: from scripts.check_topic5_hard_gap_batch_1_gate import (  # noqa: E402
   18:     _validated_evaluator_reports,
   19:     build_evaluator_reports,
   20: )
   21: 
   22: 
   23: DEFAULT_OUTPUT = ROOT / "reports" / "topic5_batch_2" / "acceptance_gate.json"
   24: REPORT_FILENAMES = {
   25:     "metadata": "metadata_contract.json",
   26:     "summary": "summary_faithfulness.json",
   27:     "consistency": "artifact_consistency.json",
   28:     "entity": "entity_passthrough.json",
   29:     "topic11": "topic11_adapter.json",
   30: }
   31: 
   32: 
   33: def load_evaluator_reports(report_dir: Path) -> dict[str, dict[str, Any]]:
   34:     reports: dict[str, dict[str, Any]] = {}
   35:     for name, filename in REPORT_FILENAMES.items():
   36:         path = report_dir / filename
   37:         if not path.is_file():
   38:             raise ValueError(f"missing evaluator report: {path}")
   39:         reports[name] = json.loads(path.read_text(encoding="utf-8"))
   40:     return reports
   41: 
   42: 
   43: def evaluate_reports(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
   44:     reports = _validated_evaluator_reports(reports)
   45:     metadata = reports["metadata"]
   46:     summary = reports["summary"]
   47:     consistency = reports["consistency"]
   48:     entity = reports["entity"]
   49:     topic11 = reports["topic11"]
   50:     values = {
   51:         "metadata_template_effective": bool(metadata["metadata_template_effective"]),
   52:         "metadata_required_localization_rate": float(
   53:             metadata["metadata_required_localization_rate"]
   54:         ),
   55:         "document_summary_faithfulness": float(
   56:             summary["document_summary_faithfulness"]
   57:         ),
   58:         "document_summary_source_coverage": float(
   59:             summary["document_summary_source_coverage"]
   60:         ),
   61:         "document_summary_new_fact_violations": int(
   62:             summary["document_summary_new_fact_violations"]
   63:         ),
   64:         "artifact_consistency_pass_rate": float(
   65:             consistency["artifact_consistency_pass_rate"]
   66:         ),
   67:         "markdown_block_coverage": float(consistency["markdown_block_coverage"]),
   68:         "chunk_source_coverage": float(consistency["chunk_source_coverage"]),
   69:         "tampering_detection_rate": float(consistency["tampering_detection_rate"]),
   70:         "entity_passthrough_coverage": float(entity["entity_passthrough_coverage"]),
   71:         "invented_entity_id_count": int(entity["invented_entity_id_count"]),
   72:         "topic11_fallback_success_rate": float(
   73:             topic11["topic11_fallback_success_rate"]
   74:         ),
   75:         "topic11_invalid_output_acceptance_count": int(
   76:             topic11["topic11_invalid_output_acceptance_count"]
   77:         ),
   78:         "secret_leak_count": int(topic11["secret_leak_count"]),
   79:         "legacy_compatibility_rate": float(topic11["legacy_compatibility_rate"]),
   80:     }
   81:     checks = {
   82:         **{
   83:             f"{name}_cases_passed": report["passed_count"] == report["case_count"]
   84:             for name, report in reports.items()
   85:         },
   86:         "metadata_template_effective": values["metadata_template_effective"] is True,
   87:         "metadata_required_localization_rate": (
   88:             values["metadata_required_localization_rate"] == 1.0
   89:         ),
   90:         "document_summary_faithfulness": (
   91:             values["document_summary_faithfulness"] == 1.0
   92:         ),
   93:         "document_summary_source_coverage": (
   94:             values["document_summary_source_coverage"] == 1.0
   95:         ),
   96:         "document_summary_new_fact_violations": (
   97:             values["document_summary_new_fact_violations"] == 0
   98:         ),
   99:         "artifact_consistency_pass_rate": (
  100:             values["artifact_consistency_pass_rate"] == 1.0
  101:         ),
  102:         "markdown_block_coverage": values["markdown_block_coverage"] == 1.0,
  103:         "chunk_source_coverage": values["chunk_source_coverage"] == 1.0,
  104:         "tampering_detection_rate": values["tampering_detection_rate"] == 1.0,
  105:         "entity_passthrough_coverage": values["entity_passthrough_coverage"] == 1.0,
  106:         "invented_entity_id_count": values["invented_entity_id_count"] == 0,
  107:         "topic11_fallback_success_rate": values["topic11_fallback_success_rate"] == 1.0,
  108:         "topic11_invalid_output_acceptance_count": (
  109:             values["topic11_invalid_output_acceptance_count"] == 0
  110:         ),
  111:         "secret_leak_count": values["secret_leak_count"] == 0,
  112:         "legacy_compatibility_rate": values["legacy_compatibility_rate"] == 1.0,
  113:     }
  114:     failed = [name for name, passed in checks.items() if not passed]
  115:     return {
  116:         "generated_at": datetime.now(UTC).isoformat(),
  117:         "passed": not failed,
  118:         "conclusion": "passed" if not failed else "failed",
  119:         "values": values,
  120:         "checks": checks,
  121:         "failed_conditions": failed,
  122:         "datasets": {
  123:             name: {
  124:                 "dataset_id": report["dataset_id"],
  125:                 "dataset_version": report["dataset_version"],
  126:                 "dataset_sha256": report["dataset_sha256"],
  127:                 "commit_sha": report["commit_sha"],
  128:                 "case_count": report["case_count"],
  129:                 "passed_count": report["passed_count"],
  130:             }
  131:             for name, report in reports.items()
  132:         },
  133:     }
  134: 
  135: 
  136: def main() -> None:
  137:     parser = argparse.ArgumentParser(description=__doc__)
  138:     parser.add_argument("--report-dir", type=Path)
  139:     parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
  140:     args = parser.parse_args()
  141:     reports = (
  142:         load_evaluator_reports(args.report_dir)
  143:         if args.report_dir is not None
  144:         else build_evaluator_reports()
  145:     )
  146:     gate = evaluate_reports(reports)
  147:     args.output.parent.mkdir(parents=True, exist_ok=True)
  148:     args.output.write_text(
  149:         json.dumps(gate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
  150:         encoding="utf-8",
  151:     )
  152:     raise SystemExit(0 if gate["passed"] else 1)
  153: 
  154: 
  155: if __name__ == "__main__":
  156:     main()

## Full file: scripts/run_topic5_batch_2_verification.py
    1: """Run cross-platform Topic 5 Batch 2 verification with raw command evidence."""
    2: 
    3: from __future__ import annotations
    4: 
    5: import argparse
    6: import json
    7: import platform
    8: import re
    9: import subprocess
   10: import sys
   11: import time
   12: from dataclasses import dataclass
   13: from datetime import UTC, datetime
   14: from pathlib import Path
   15: from typing import Any
   16: 
   17: 
   18: ROOT = Path(__file__).resolve().parents[1]
   19: BACKEND = ROOT / "backend"
   20: FRONTEND = ROOT / "frontend"
   21: DEFAULT_OUTPUT = ROOT / "reports" / "topic5_batch_2" / "verification"
   22: 
   23: 
   24: @dataclass(frozen=True)
   25: class CommandSpec:
   26:     name: str
   27:     command: tuple[str, ...]
   28:     cwd: Path
   29:     mandatory: bool = True
   30: 
   31: 
   32: def npm_executable(current_platform: str | None = None) -> str:
   33:     return "npm.cmd" if (current_platform or sys.platform) == "win32" else "npm"
   34: 
   35: 
   36: def command_specs(output_dir: Path = DEFAULT_OUTPUT) -> list[CommandSpec]:
   37:     npm = npm_executable()
   38:     evaluator_output = output_dir / "evaluator_reports"
   39:     return [
   40:         CommandSpec(
   41:             "backend-tests",
   42:             (sys.executable, "-m", "pytest", "-q"),
   43:             BACKEND,
   44:         ),
   45:         CommandSpec(
   46:             "ruff",
   47:             (sys.executable, "-m", "ruff", "check", "."),
   48:             BACKEND,
   49:         ),
   50:         CommandSpec("frontend-tests", (npm, "run", "test"), FRONTEND),
   51:         CommandSpec("frontend-build", (npm, "run", "build"), FRONTEND),
   52:         CommandSpec(
   53:             "openapi-drift",
   54:             (sys.executable, "scripts/export_openapi.py", "--check"),
   55:             ROOT,
   56:         ),
   57:         CommandSpec(
   58:             "schemapack-contract-gate",
   59:             (sys.executable, "scripts/check_schema_pack_contract_gate.py"),
   60:             ROOT,
   61:         ),
   62:         *[
   63:             CommandSpec(
   64:                 f"evaluator-{name}",
   65:                 (
   66:                     sys.executable,
   67:                     f"scripts/eval_topic5_{name}.py",
   68:                     "--output",
   69:                     str(evaluator_output / f"{name}.json"),
   70:                 ),
   71:                 ROOT,
   72:             )
   73:             for name in (
   74:                 "metadata_contract",
   75:                 "summary_faithfulness",
   76:                 "artifact_consistency",
   77:                 "entity_passthrough",
   78:                 "topic11_adapter",
   79:             )
   80:         ],
   81:         CommandSpec(
   82:             "batch2-acceptance-gate",
   83:             (
   84:                 sys.executable,
   85:                 "scripts/check_topic5_batch_2_acceptance_gate.py",
   86:                 "--report-dir",
   87:                 str(evaluator_output),
   88:                 "--output",
   89:                 str(output_dir / "acceptance_gate.json"),
   90:             ),
   91:             ROOT,
   92:         ),
   93:     ]
   94: 
   95: 
   96: def enforce_clean_tree(status_output: str, *, allow_dirty: bool) -> bool:
   97:     dirty = bool(status_output.strip())
   98:     if dirty and not allow_dirty:
   99:         raise RuntimeError("git working tree is dirty; rerun with --allow-dirty to override")
  100:     return dirty
  101: 
  102: 
  103: def git_status(root: Path = ROOT) -> str:
  104:     completed = subprocess.run(
  105:         ["git", "status", "--porcelain", "--untracked-files=all"],
  106:         cwd=root,
  107:         check=True,
  108:         capture_output=True,
  109:         text=True,
  110:     )
  111:     return completed.stdout
  112: 
  113: 
  114: def git_commit_sha(root: Path = ROOT) -> str:
  115:     completed = subprocess.run(
  116:         ["git", "rev-parse", "HEAD"],
  117:         cwd=root,
  118:         check=True,
  119:         capture_output=True,
  120:         text=True,
  121:     )
  122:     return completed.stdout.strip()
  123: 
  124: 
  125: def skipped_result(spec: CommandSpec, reason: str) -> dict[str, Any]:
  126:     return {
  127:         "name": spec.name,
  128:         "command": list(spec.command),
  129:         "cwd": str(spec.cwd),
  130:         "stdout": "",
  131:         "stderr": reason,
  132:         "return_code": None,
  133:         "duration_seconds": 0.0,
  134:         "mandatory": spec.mandatory,
  135:         "status": "skipped",
  136:         "passed": False if spec.mandatory else True,
  137:         "raw_log": None,
  138:     }
  139: 
  140: 
  141: def run_command(spec: CommandSpec, log_dir: Path) -> dict[str, Any]:
  142:     log_dir.mkdir(parents=True, exist_ok=True)
  143:     started = time.perf_counter()
  144:     try:
  145:         completed = subprocess.run(
  146:             list(spec.command),
  147:             cwd=spec.cwd,
  148:             check=False,
  149:             capture_output=True,
  150:             text=True,
  151:         )
  152:     except FileNotFoundError as exc:
  153:         result = skipped_result(spec, str(exc))
  154:     else:
  155:         result = {
  156:             "name": spec.name,
  157:             "command": list(spec.command),
  158:             "cwd": str(spec.cwd),
  159:             "stdout": completed.stdout,
  160:             "stderr": completed.stderr,
  161:             "return_code": completed.returncode,
  162:             "duration_seconds": time.perf_counter() - started,
  163:             "mandatory": spec.mandatory,
  164:             "status": "passed" if completed.returncode == 0 else "failed",
  165:             "passed": completed.returncode == 0,
  166:             "raw_log": None,
  167:         }
  168:     result["duration_seconds"] = max(
  169:         float(result["duration_seconds"]), time.perf_counter() - started
  170:     )
  171:     log_path = log_dir / f"{_safe_name(spec.name)}.log"
  172:     log_path.write_text(_render_raw_log(result), encoding="utf-8")
  173:     result["raw_log"] = str(log_path.resolve())
  174:     return result
  175: 
  176: 
  177: def _safe_name(value: str) -> str:
  178:     return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "command"
  179: 
  180: 
  181: def _render_raw_log(result: dict[str, Any]) -> str:
  182:     command = subprocess.list2cmdline(result["command"])
  183:     return (
  184:         f"command: {command}\n"
  185:         f"cwd: {result['cwd']}\n"
  186:         f"status: {result['status']}\n"
  187:         f"return_code: {result['return_code']}\n"
  188:         f"duration_seconds: {result['duration_seconds']:.6f}\n"
  189:         "\n[stdout]\n"
  190:         f"{result['stdout']}"
  191:         "\n[stderr]\n"
  192:         f"{result['stderr']}\n"
  193:     )
  194: 
  195: 
  196: def tool_versions() -> dict[str, str]:
  197:     npm = npm_executable()
  198:     return {
  199:         "python": platform.python_version(),
  200:         "platform": platform.platform(),
  201:         "git": _version(["git", "--version"]),
  202:         "node": _version(["node", "--version"]),
  203:         "npm": _version([npm, "--version"]),
  204:     }
  205: 
  206: 
  207: def _version(command: list[str]) -> str:
  208:     try:
  209:         completed = subprocess.run(
  210:             command,
  211:             cwd=ROOT,
  212:             check=False,
  213:             capture_output=True,
  214:             text=True,
  215:         )
  216:     except FileNotFoundError:
  217:         return "unavailable"
  218:     output = (completed.stdout or completed.stderr).strip()
  219:     return output if completed.returncode == 0 and output else "unavailable"
  220: 
  221: 
  222: def write_summary(
  223:     output_dir: Path,
  224:     *,
  225:     commit_sha: str,
  226:     dirty: bool,
  227:     allow_dirty: bool,
  228:     records: list[dict[str, Any]],
  229:     tool_versions: dict[str, str],
  230: ) -> Path:
  231:     output_dir.mkdir(parents=True, exist_ok=True)
  232:     mandatory = [record for record in records if record["mandatory"]]
  233:     payload = {
  234:         "generated_at": datetime.now(UTC).isoformat(),
  235:         "commit_sha": commit_sha,
  236:         "dirty_tree": dirty,
  237:         "allow_dirty": allow_dirty,
  238:         "tool_versions": tool_versions,
  239:         "commands": records,
  240:         "passed": bool(mandatory) and all(record["passed"] for record in mandatory),
  241:         "full_backend_tests_passed": _named_passed(records, "backend-tests"),
  242:         "ruff_clean": _named_passed(records, "ruff"),
  243:         "frontend_tests_passed": _named_passed(records, "frontend-tests"),
  244:         "frontend_build_passed": _named_passed(records, "frontend-build"),
  245:         "openapi_export_passed": _named_passed(records, "openapi-drift"),
  246:         "schema_pack_contract_gate_passed": _named_passed(
  247:             records, "schemapack-contract-gate"
  248:         ),
  249:         "batch2_acceptance_gate_passed": _named_passed(
  250:             records, "batch2-acceptance-gate"
  251:         ),
  252:     }
  253:     path = output_dir / "verification_summary.json"
  254:     path.write_text(
  255:         json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
  256:         encoding="utf-8",
  257:     )
  258:     return path
  259: 
  260: 
  261: def _named_passed(records: list[dict[str, Any]], name: str) -> bool:
  262:     return any(record["name"] == name and record["passed"] for record in records)
  263: 
  264: 
  265: def main() -> None:
  266:     parser = argparse.ArgumentParser(description=__doc__)
  267:     parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
  268:     parser.add_argument("--allow-dirty", action="store_true")
  269:     args = parser.parse_args()
  270: 
  271:     commit_sha = git_commit_sha()
  272:     try:
  273:         dirty = enforce_clean_tree(git_status(), allow_dirty=args.allow_dirty)
  274:     except RuntimeError as exc:
  275:         print(str(exc), file=sys.stderr)
  276:         raise SystemExit(2) from None
  277: 
  278:     records = [
  279:         run_command(spec, args.output_dir / "raw_logs")
  280:         for spec in command_specs(args.output_dir)
  281:     ]
  282:     summary_path = write_summary(
  283:         args.output_dir,
  284:         commit_sha=commit_sha,
  285:         dirty=dirty,
  286:         allow_dirty=args.allow_dirty,
  287:         records=records,
  288:         tool_versions=tool_versions(),
  289:     )
  290:     payload = json.loads(summary_path.read_text(encoding="utf-8"))
  291:     print(f"wrote verification summary to {summary_path}")
  292:     raise SystemExit(0 if payload["passed"] else 1)
  293: 
  294: 
  295: if __name__ == "__main__":
  296:     main()

## Full file: scripts/export_openapi.py
    1: """Export the FastAPI OpenAPI schema for local docs and frontend reference."""
    2: 
    3: import argparse
    4: import json
    5: import sys
    6: from pathlib import Path
    7: from typing import Any
    8: 
    9: 
   10: ROOT = Path(__file__).resolve().parents[1]
   11: BACKEND_DIR = ROOT / "backend"
   12: if str(BACKEND_DIR) not in sys.path:
   13:     sys.path.insert(0, str(BACKEND_DIR))
   14: 
   15: from app.main import create_app  # noqa: E402
   16: 
   17: 
   18: def _serialized_schema(schema: dict[str, Any]) -> str:
   19:     return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
   20: 
   21: 
   22: def export_openapi(output_path: Path) -> dict[str, Any]:
   23:     schema = create_app().openapi()
   24:     output_path.parent.mkdir(parents=True, exist_ok=True)
   25:     output_path.write_text(_serialized_schema(schema), encoding="utf-8")
   26:     return schema
   27: 
   28: 
   29: def check_openapi_drift(expected_path: Path) -> bool:
   30:     if not expected_path.is_file():
   31:         return False
   32:     actual = _serialized_schema(create_app().openapi())
   33:     return expected_path.read_text(encoding="utf-8") == actual
   34: 
   35: 
   36: def main() -> None:
   37:     parser = argparse.ArgumentParser(description=__doc__)
   38:     parser.add_argument(
   39:         "--output",
   40:         type=Path,
   41:         default=ROOT / "docs" / "openapi.json",
   42:         help="Path to write the OpenAPI JSON schema.",
   43:     )
   44:     parser.add_argument(
   45:         "--check",
   46:         action="store_true",
   47:         help="Exit nonzero when the committed OpenAPI JSON differs; do not rewrite it.",
   48:     )
   49:     args = parser.parse_args()
   50:     if args.check:
   51:         if not check_openapi_drift(args.output):
   52:             print(f"OpenAPI drift detected for {args.output}")
   53:             raise SystemExit(1)
   54:         print(f"OpenAPI schema is current: {args.output}")
   55:         return
   56:     schema = export_openapi(args.output)
   57:     print(f"exported {len(schema.get('paths', {}))} paths to {args.output}")
   58: 
   59: 
   60: if __name__ == "__main__":
   61:     main()

## Full file: .github/workflows/ci.yml
    1: name: CI
    2: 
    3: on:
    4:   push:
    5:   pull_request:
    6: 
    7: jobs:
    8:   topic5-batch-2-verification:
    9:     strategy:
   10:       fail-fast: false
   11:       matrix:
   12:         os: [windows-latest, ubuntu-latest]
   13:     runs-on: ${{ matrix.os }}
   14:     steps:
   15:       - uses: actions/checkout@v4
   16:       - uses: actions/setup-python@v5
   17:         with:
   18:           python-version: "3.13"
   19:       - uses: actions/setup-node@v4
   20:         with:
   21:           node-version: "20"
   22:           cache: npm
   23:           cache-dependency-path: frontend/package-lock.json
   24:       - name: Install backend dependencies
   25:         run: python -m pip install -r backend/requirements.txt
   26:       - name: Install frontend dependencies
   27:         working-directory: frontend
   28:         run: npm ci
   29:       - name: Run Topic 5 Batch 2 verification
   30:         run: python scripts/run_topic5_batch_2_verification.py
   31:       - name: Upload verification evidence
   32:         if: always()
   33:         uses: actions/upload-artifact@v4
   34:         with:
   35:           name: topic5-batch-2-${{ runner.os }}
   36:           path: reports/topic5_batch_2/verification
   37:           if-no-files-found: warn

## Full file: backend/tests/test_topic5_batch_2_evaluator_reports.py
    1: from __future__ import annotations
    2: 
    3: import copy
    4: import hashlib
    5: import importlib.util
    6: import json
    7: from pathlib import Path
    8: from types import ModuleType
    9: 
   10: import pytest
   11: 
   12: ROOT = Path(__file__).resolve().parents[2]
   13: REQUIRED_REPORT_FIELDS = {
   14:     "dataset_id",
   15:     "dataset_version",
   16:     "dataset_sha256",
   17:     "commit_sha",
   18:     "case_count",
   19:     "passed_count",
   20:     "failed_cases",
   21:     "reproduction_command",
   22:     "claim_boundary",
   23: }
   24: EVALUATORS = {
   25:     "metadata_contract": {
   26:         "metrics": {
   27:             "metadata_template_effectiveness_rate": 1.0,
   28:             "metadata_required_localization_rate": 1.0,
   29:         }
   30:     },
   31:     "summary_faithfulness": {
   32:         "metrics": {
   33:             "document_summary_faithfulness": 1.0,
   34:             "document_summary_source_coverage": 1.0,
   35:             "document_summary_new_fact_violations": 0,
   36:         }
   37:     },
   38:     "artifact_consistency": {
   39:         "metrics": {
   40:             "artifact_consistency_pass_rate": 1.0,
   41:             "markdown_block_coverage": 1.0,
   42:             "chunk_source_coverage": 1.0,
   43:             "tampering_detection_rate": 1.0,
   44:         }
   45:     },
   46:     "entity_passthrough": {
   47:         "metrics": {
   48:             "entity_passthrough_coverage": 1.0,
   49:             "invented_entity_id_count": 0,
   50:         }
   51:     },
   52:     "topic11_adapter": {
   53:         "metrics": {
   54:             "topic11_fallback_success_rate": 1.0,
   55:             "topic11_invalid_output_acceptance_count": 0,
   56:             "secret_leak_count": 0,
   57:             "legacy_compatibility_rate": 1.0,
   58:         }
   59:     },
   60: }
   61: 
   62: 
   63: def _load_script(name: str) -> ModuleType:
   64:     path = ROOT / "scripts" / f"eval_topic5_{name}.py"
   65:     assert path.is_file(), f"missing evaluator: {path}"
   66:     spec = importlib.util.spec_from_file_location(f"eval_topic5_{name}", path)
   67:     assert spec and spec.loader
   68:     module = importlib.util.module_from_spec(spec)
   69:     spec.loader.exec_module(module)
   70:     return module
   71: 
   72: 
   73: @pytest.mark.parametrize(("name", "contract"), EVALUATORS.items())
   74: def test_batch_2_evaluator_report_contract(name: str, contract: dict) -> None:
   75:     module = _load_script(name)
   76:     report = module.build_report()
   77:     fixture_path = ROOT / "eval" / f"topic5_{name}" / "v2" / "cases.json"
   78:     fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
   79: 
   80:     assert REQUIRED_REPORT_FIELDS <= report.keys()
   81:     assert report["dataset_id"] == fixture["dataset_id"]
   82:     assert report["dataset_version"] == fixture["version"]
   83:     assert report["dataset_sha256"] == hashlib.sha256(fixture_path.read_bytes()).hexdigest()
   84:     assert report["case_count"] == len(fixture["cases"])
   85:     assert report["case_count"] > 0
   86:     assert report["passed_count"] == report["case_count"]
   87:     assert report["failed_cases"] == []
   88:     assert len(report["commit_sha"]) == 40
   89:     assert report["reproduction_command"]
   90:     assert report["claim_boundary"]
   91:     for metric, expected in contract["metrics"].items():
   92:         assert report[metric] == expected
   93: 
   94: 
   95: def test_metadata_evaluator_counts_a_declared_case_failure(tmp_path: Path) -> None:
   96:     module = _load_script("metadata_contract")
   97:     fixture = json.loads(module.DEFAULT_FIXTURE.read_text(encoding="utf-8"))
   98:     fixture["cases"][0]["expected_document_metadata"] = {"wrong": "value"}
   99:     mutated = tmp_path / "cases.json"
  100:     mutated.write_text(json.dumps(fixture), encoding="utf-8")
  101: 
  102:     report = module.build_report(mutated)
  103: 
  104:     assert report["case_count"] == len(fixture["cases"])
  105:     assert report["passed_count"] == report["case_count"] - 1
  106:     assert [case["case_id"] for case in report["failed_cases"]] == [
  107:         fixture["cases"][0]["case_id"]
  108:     ]
  109: 
  110: 
  111: def test_gate_uses_evaluator_reports_and_rejects_component_proxies() -> None:
  112:     from scripts.check_topic5_hard_gap_batch_1_gate import evaluate_gate
  113: 
  114:     evaluator_reports = {
  115:         "metadata": _load_script("metadata_contract").build_report(),
  116:         "summary": _load_script("summary_faithfulness").build_report(),
  117:         "consistency": _load_script("artifact_consistency").build_report(),
  118:         "entity": _load_script("entity_passthrough").build_report(),
  119:         "topic11": _load_script("topic11_adapter").build_report(),
  120:     }
  121:     operations = {
  122:         "field_operation_accuracy": 1.0,
  123:         "rename_accuracy": 1.0,
  124:         "merge_accuracy": 1.0,
  125:         "split_accuracy": 1.0,
  126:         "unsafe_operation_count": 0,
  127:         "dataset_sha256": "operations",
  128:     }
  129:     localization = {
  130:         "schema_localization_rate": 1.0,
  131:         "error_code_accuracy": 1.0,
  132:         "stage_accuracy": 1.0,
  133:         "dataset_sha256": "localization",
  134:     }
  135:     tag_quality = {
  136:         "metrics": {
  137:             "content_tag_f1": 1.0,
  138:             "management_tag_f1": 1.0,
  139:             "quality_tag_f1": 1.0,
  140:             "unknown_tag_count": 0,
  141:         }
  142:     }
  143:     verification = {
  144:         "full_backend_tests_passed": True,
  145:         "ruff_clean": True,
  146:         "frontend_tests_passed": True,
  147:         "openapi_export_passed": True,
  148:     }
  149:     components = {
  150:         name: {"passed": True}
  151:         for name in ("metadata", "summary", "consistency", "entity", "topic11", "legacy")
  152:     }
  153: 
  154:     passed = evaluate_gate(
  155:         operations=operations,
  156:         localization=localization,
  157:         tag_quality=tag_quality,
  158:         components=components,
  159:         evaluator_reports=evaluator_reports,
  160:         verification=verification,
  161:     )
  162:     assert passed["conclusion"] == "passed"
  163: 
  164:     mutated = copy.deepcopy(evaluator_reports)
  165:     mutated["summary"]["document_summary_faithfulness"] = 0.5
  166:     failed = evaluate_gate(
  167:         operations=operations,
  168:         localization=localization,
  169:         tag_quality=tag_quality,
  170:         components=components,
  171:         evaluator_reports=mutated,
  172:         verification=verification,
  173:     )
  174:     assert failed["conclusion"] == "failed"
  175:     assert "document_summary_faithfulness" in failed["failed_conditions"]
  176: 
  177:     with pytest.raises(ValueError, match="evaluator report"):
  178:         evaluate_gate(
  179:             operations=operations,
  180:             localization=localization,
  181:             tag_quality=tag_quality,
  182:             components=components,
  183:             evaluator_reports={},
  184:             verification=verification,
  185:         )
  186: 
  187: 
  188: def test_batch_2_acceptance_gate_fails_a_mutated_case_metric() -> None:
  189:     path = ROOT / "scripts" / "check_topic5_batch_2_acceptance_gate.py"
  190:     assert path.is_file(), f"missing acceptance gate: {path}"
  191:     spec = importlib.util.spec_from_file_location("topic5_batch2_acceptance", path)
  192:     assert spec and spec.loader
  193:     module = importlib.util.module_from_spec(spec)
  194:     spec.loader.exec_module(module)
  195: 
  196:     reports = {
  197:         "metadata": _load_script("metadata_contract").build_report(),
  198:         "summary": _load_script("summary_faithfulness").build_report(),
  199:         "consistency": _load_script("artifact_consistency").build_report(),
  200:         "entity": _load_script("entity_passthrough").build_report(),
  201:         "topic11": _load_script("topic11_adapter").build_report(),
  202:     }
  203:     passed = module.evaluate_reports(reports)
  204:     assert passed["passed"] is True
  205: 
  206:     mutated = copy.deepcopy(reports)
  207:     mutated["consistency"]["tampering_detection_rate"] = 0.5
  208:     failed = module.evaluate_reports(mutated)
  209:     assert failed["passed"] is False
  210:     assert "tampering_detection_rate" in failed["failed_conditions"]

## Full file: backend/tests/test_topic5_batch_2_verification_runner.py
    1: from __future__ import annotations
    2: 
    3: import importlib.util
    4: import json
    5: import sys
    6: from pathlib import Path
    7: from types import ModuleType
    8: 
    9: import pytest
   10: 
   11: ROOT = Path(__file__).resolve().parents[2]
   12: 
   13: 
   14: def _load_runner() -> ModuleType:
   15:     path = ROOT / "scripts" / "run_topic5_batch_2_verification.py"
   16:     assert path.is_file(), f"missing verification runner: {path}"
   17:     spec = importlib.util.spec_from_file_location("topic5_batch2_runner", path)
   18:     assert spec and spec.loader
   19:     module = importlib.util.module_from_spec(spec)
   20:     sys.modules[spec.name] = module
   21:     spec.loader.exec_module(module)
   22:     return module
   23: 
   24: 
   25: def test_dirty_tree_requires_explicit_override() -> None:
   26:     runner = _load_runner()
   27: 
   28:     with pytest.raises(RuntimeError, match="dirty"):
   29:         runner.enforce_clean_tree(" M scripts/example.py\n", allow_dirty=False)
   30: 
   31:     assert runner.enforce_clean_tree(" M scripts/example.py\n", allow_dirty=True) is True
   32:     assert runner.enforce_clean_tree("", allow_dirty=False) is False
   33: 
   34: 
   35: def test_skipped_mandatory_command_is_not_passed() -> None:
   36:     runner = _load_runner()
   37:     spec = runner.CommandSpec(
   38:         name="mandatory",
   39:         command=(sys.executable, "-c", "pass"),
   40:         cwd=ROOT,
   41:         mandatory=True,
   42:     )
   43: 
   44:     result = runner.skipped_result(spec, "tool unavailable")
   45: 
   46:     assert result["status"] == "skipped"
   47:     assert result["passed"] is False
   48:     assert result["return_code"] is None
   49: 
   50: 
   51: def test_command_capture_writes_non_empty_raw_log(tmp_path: Path) -> None:
   52:     runner = _load_runner()
   53:     spec = runner.CommandSpec(
   54:         name="capture",
   55:         command=(
   56:             sys.executable,
   57:             "-c",
   58:             "import sys; print('stdout-line'); print('stderr-line', file=sys.stderr)",
   59:         ),
   60:         cwd=ROOT,
   61:         mandatory=True,
   62:     )
   63: 
   64:     result = runner.run_command(spec, tmp_path)
   65: 
   66:     assert result["command"][0] == sys.executable
   67:     assert result["cwd"] == str(ROOT)
   68:     assert result["stdout"].strip() == "stdout-line"
   69:     assert result["stderr"].strip() == "stderr-line"
   70:     assert result["return_code"] == 0
   71:     assert result["duration_seconds"] >= 0
   72:     assert result["passed"] is True
   73:     raw_log = Path(result["raw_log"])
   74:     assert raw_log.is_file()
   75:     assert raw_log.stat().st_size > 0
   76: 
   77: 
   78: def test_summary_is_actual_json_and_fails_for_skipped_mandatory(
   79:     tmp_path: Path,
   80: ) -> None:
   81:     runner = _load_runner()
   82:     spec = runner.CommandSpec(
   83:         name="mandatory",
   84:         command=(sys.executable, "-c", "pass"),
   85:         cwd=ROOT,
   86:         mandatory=True,
   87:     )
   88:     skipped = runner.skipped_result(spec, "tool unavailable")
   89: 
   90:     path = runner.write_summary(
   91:         tmp_path,
   92:         commit_sha="a" * 40,
   93:         dirty=True,
   94:         allow_dirty=True,
   95:         records=[skipped],
   96:         tool_versions={"python": sys.version.split()[0]},
   97:     )
   98:     payload = json.loads(path.read_text(encoding="utf-8"))
   99: 
  100:     assert path.name == "verification_summary.json"
  101:     assert path.stat().st_size > 0
  102:     assert payload["commit_sha"] == "a" * 40
  103:     assert payload["passed"] is False
  104:     assert payload["commands"][0]["status"] == "skipped"
  105: 
  106: 
  107: def test_cross_platform_command_selection_uses_current_python() -> None:
  108:     runner = _load_runner()
  109: 
  110:     assert runner.npm_executable("win32") == "npm.cmd"
  111:     assert runner.npm_executable("linux") == "npm"
  112:     assert all(
  113:         spec.command[0] in {sys.executable, "npm", "npm.cmd"}
  114:         for spec in runner.command_specs()
  115:     )

## Full file: backend/tests/test_topic5_batch_2_ci.py
    1: from pathlib import Path
    2: 
    3: ROOT = Path(__file__).resolve().parents[2]
    4: 
    5: 
    6: def test_ci_runs_batch_2_verification_on_windows_and_linux() -> None:
    7:     workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
    8:         encoding="utf-8"
    9:     )
   10:     runner = (ROOT / "scripts" / "run_topic5_batch_2_verification.py").read_text(
   11:         encoding="utf-8"
   12:     )
   13: 
   14:     for marker in (
   15:         "matrix.os",
   16:         "windows-latest",
   17:         "ubuntu-latest",
   18:         "actions/setup-python@v5",
   19:         "actions/setup-node@v4",
   20:         "python -m pip install -r backend/requirements.txt",
   21:         "npm ci",
   22:         "python scripts/run_topic5_batch_2_verification.py",
   23:     ):
   24:         assert marker in workflow
   25: 
   26:     for marker in (
   27:         '"backend-tests"',
   28:         '"ruff"',
   29:         '"frontend-tests"',
   30:         '"frontend-build"',
   31:         '"openapi-drift"',
   32:         '"schemapack-contract-gate"',
   33:         '"batch2-acceptance-gate"',
   34:     ):
   35:         assert marker in runner
   36: 
   37:     assert "secrets." not in workflow

## Full file: backend/tests/test_topic5_hard_gap_evaluators.py
    1: from __future__ import annotations
    2: 
    3: import copy
    4: import json
    5: from pathlib import Path
    6: 
    7: import pytest
    8: from scripts.check_topic5_hard_gap_batch_1_gate import (
    9:     build_evaluator_reports,
   10:     evaluate_gate,
   11: )
   12: from scripts.eval_topic5_field_operations import build_report as field_report
   13: from scripts.eval_topic5_field_operations import load_fixture as load_field_fixture
   14: from scripts.eval_topic5_schema_localization import (
   15:     build_report as localization_report,
   16: )
   17: from scripts.eval_topic5_schema_localization import (
   18:     load_fixture as load_localization_fixture,
   19: )
   20: 
   21: ROOT = Path(__file__).resolve().parents[2]
   22: 
   23: 
   24: def test_field_operation_evaluator_has_fixed_119_case_denominator() -> None:
   25:     report = field_report()
   26: 
   27:     assert report["case_count"] == 119
   28:     assert report["field_operation_accuracy"] >= 0.95
   29:     assert report["rename_accuracy"] >= 0.95
   30:     assert report["merge_accuracy"] >= 0.95
   31:     assert report["split_accuracy"] >= 0.95
   32:     assert report["unsafe_operation_count"] == 0
   33: 
   34: 
   35: def test_schema_localization_evaluator_has_fixed_40_case_denominator() -> None:
   36:     report = localization_report()
   37: 
   38:     assert report["case_count"] == 40
   39:     assert report["schema_localization_rate"] == 1.0
   40:     assert report["error_code_accuracy"] == 1.0
   41:     assert report["stage_accuracy"] == 1.0
   42: 
   43: 
   44: def test_field_fixture_rejects_reduced_category_denominator(tmp_path: Path) -> None:
   45:     source = ROOT / "eval" / "topic5_field_operations" / "v1" / "cases.json"
   46:     payload = json.loads(source.read_text(encoding="utf-8"))
   47:     payload["groups"][0]["variants"].pop()
   48:     path = tmp_path / "reduced.json"
   49:     path.write_text(json.dumps(payload), encoding="utf-8")
   50: 
   51:     with pytest.raises(ValueError, match="requires 20 rename cases"):
   52:         load_field_fixture(path)
   53: 
   54: 
   55: def test_localization_fixture_rejects_reduced_denominator(tmp_path: Path) -> None:
   56:     source = ROOT / "eval" / "topic5_schema_localization" / "v1" / "cases.json"
   57:     payload = json.loads(source.read_text(encoding="utf-8"))
   58:     payload["cases"].pop()
   59:     path = tmp_path / "reduced.json"
   60:     path.write_text(json.dumps(payload), encoding="utf-8")
   61: 
   62:     with pytest.raises(ValueError, match="at least 40 cases"):
   63:         load_localization_fixture(path)
   64: 
   65: 
   66: def test_gate_passes_all_thresholds_and_fails_mutated_metric() -> None:
   67:     operations = field_report()
   68:     localization = localization_report()
   69:     tag_quality = json.loads(
   70:         (
   71:             ROOT
   72:             / "docs"
   73:             / "浜ゆ帴"
   74:             / "evidence"
   75:             / "hard_gap_batch_1"
   76:             / "tags"
   77:             / "content_tag_quality.json"
   78:         ).read_text(encoding="utf-8")
   79:     )
   80:     components = {
   81:         name: {"passed": True}
   82:         for name in ("metadata", "summary", "consistency", "entity", "topic11", "legacy")
   83:     }
   84:     verification = {
   85:         "full_backend_tests_passed": True,
   86:         "ruff_clean": True,
   87:         "frontend_tests_passed": True,
   88:         "openapi_export_passed": True,
   89:     }
   90:     evaluator_reports = build_evaluator_reports()
   91: 
   92:     passed = evaluate_gate(
   93:         operations=operations,
   94:         localization=localization,
   95:         tag_quality=tag_quality,
   96:         components=components,
   97:         evaluator_reports=evaluator_reports,
   98:         verification=verification,
   99:     )
  100:     assert passed["conclusion"] == "passed"
  101: 
  102:     failed_operations = copy.deepcopy(operations)
  103:     failed_operations["merge_accuracy"] = 0.94
  104:     failed = evaluate_gate(
  105:         operations=failed_operations,
  106:         localization=localization,
  107:         tag_quality=tag_quality,
  108:         components=components,
  109:         evaluator_reports=evaluator_reports,
  110:         verification=verification,
  111:     )
  112:     assert failed["conclusion"] == "failed"
  113:     assert failed["failed_conditions"] == ["merge_accuracy"]

## Full file: backend/tests/test_openapi_export.py
    1: import importlib.util
    2: import json
    3: from pathlib import Path
    4: 
    5: ROOT = Path(__file__).resolve().parents[2]
    6: EXPORT_SCRIPT = ROOT / "scripts" / "export_openapi.py"
    7: 
    8: 
    9: def load_export_module():
   10:     spec = importlib.util.spec_from_file_location("export_openapi", EXPORT_SCRIPT)
   11:     assert spec is not None
   12:     assert spec.loader is not None
   13:     module = importlib.util.module_from_spec(spec)
   14:     spec.loader.exec_module(module)
   15:     return module
   16: 
   17: 
   18: def test_openapi_export_includes_demo_workflow_paths(tmp_path):
   19:     module = load_export_module()
   20: 
   21:     output = tmp_path / "openapi.json"
   22:     schema = module.export_openapi(output)
   23:     written = json.loads(output.read_text(encoding="utf-8"))
   24: 
   25:     assert written == schema
   26:     for path in [
   27:         "/api/v1/documents/import",
   28:         "/api/v1/schemas",
   29:         "/api/v1/templates",
   30:         "/api/v1/tasks",
   31:         "/api/v1/tasks/{task_id}/execute",
   32:         "/api/v1/tasks/{task_id}/reports/{report_name}",
   33:         "/api/v1/tasks/{task_id}/package/download",
   34:     ]:
   35:         assert path in schema["paths"]
   36: 
   37: 
   38: def test_openapi_check_detects_drift_without_rewriting_expected_file(tmp_path):
   39:     module = load_export_module()
   40:     expected = tmp_path / "openapi.json"
   41:     module.export_openapi(expected)
   42:     original = expected.read_bytes()
   43: 
   44:     assert module.check_openapi_drift(expected) is True
   45:     assert expected.read_bytes() == original
   46: 
   47:     expected.write_text("{}\n", encoding="utf-8")
   48:     drifted = expected.read_bytes()
   49:     assert module.check_openapi_drift(expected) is False
   50:     assert expected.read_bytes() == drifted
