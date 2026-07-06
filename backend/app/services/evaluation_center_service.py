import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.schemas.evaluation_center import (
    DatasetRegistryItem,
    EvaluationMetricCard,
    EvaluationRun,
    EvaluationScorecard,
    EvaluationScorecardSummary,
    MetricDefinition,
)
from app.services.dataset_registry_service import DatasetRegistryService
from app.services.metric_registry_service import MetricRegistryService
from app.services.storage_service import StorageService
from app.utils.ids import new_id

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCORECARD_METRICS: tuple[dict[str, Any], ...] = (
    {
        "metric_id": "package_verification_rate",
        "name": "Package Verification",
        "target": 1.0,
        "direction": "higher",
        "hard_gate": True,
        "explanation": "Package structure, manifest, hashes and traceability are valid.",
    },
    {
        "metric_id": "mapping_recall",
        "name": "Mapping Recall",
        "target": 0.6,
        "direction": "higher",
        "hard_gate": False,
        "explanation": "Expected mapping signals recovered by deterministic mapping or review.",
    },
    {
        "metric_id": "strict_validation_rate",
        "name": "Strict Validation",
        "target": 0.7,
        "direction": "higher",
        "hard_gate": False,
        "explanation": "Semantic field validation is tracked separately from package verification.",
    },
    {
        "metric_id": "review_required_count",
        "name": "Review Required",
        "target": 60,
        "direction": "lower",
        "hard_gate": False,
        "explanation": "Ambiguous mappings remain queued for human review.",
    },
    {
        "metric_id": "required_missing_count",
        "name": "Required Missing",
        "target": 4,
        "direction": "lower",
        "hard_gate": False,
        "explanation": "Required semantic fields not confirmed by deterministic evidence.",
    },
    {
        "metric_id": "badcase_violation_count",
        "name": "Badcase Safety",
        "target": 0,
        "direction": "lower",
        "hard_gate": True,
        "explanation": "Forbidden high-risk mappings must never be auto-accepted.",
    },
    {
        "metric_id": "llm_auto_accepted_count",
        "name": "LLM Auto Accept",
        "target": 0,
        "direction": "lower",
        "hard_gate": True,
        "explanation": "LLM suggestions always require review and are never auto-accepted.",
    },
    {
        "metric_id": "adapter_trace_coverage",
        "name": "Adapter Trace Coverage",
        "target": 0.95,
        "direction": "higher",
        "hard_gate": True,
        "explanation": "Converted blocks retain deterministic external source paths.",
    },
    {
        "metric_id": "router_top1_accuracy",
        "name": "Router Accuracy",
        "target": 0.85,
        "direction": "higher",
        "hard_gate": False,
        "explanation": "Expanded fixtures route to the expected schema/template contract.",
    },
    {
        "metric_id": "downstream_contract_pass_rate",
        "name": "Downstream Contract",
        "target": 1.0,
        "direction": "higher",
        "hard_gate": True,
        "explanation": "Published packages satisfy the versioned downstream contract.",
    },
    {
        "metric_id": "lineage_parse_pass_rate",
        "name": "Lineage Parse",
        "target": 1.0,
        "direction": "higher",
        "hard_gate": True,
        "explanation": "Every persisted lineage graph validates against the Lineage 1.0 schema.",
    },
    {
        "metric_id": "lineage_field_coverage",
        "name": "Lineage Field Coverage",
        "target": 0.9,
        "direction": "higher",
        "hard_gate": True,
        "explanation": "Target fields retain a traceable path to mapping and source evidence.",
    },
    {
        "metric_id": "lineage_broken_edges",
        "name": "Lineage Broken Edges",
        "target": 0,
        "direction": "lower",
        "hard_gate": True,
        "explanation": "Every lineage edge must reference existing source and target nodes.",
    },
    {
        "metric_id": "lineage_secret_leaks",
        "name": "Lineage Secret Safety",
        "target": 0,
        "direction": "lower",
        "hard_gate": True,
        "explanation": "Lineage metadata must not expose credentials or secret-like values.",
    },
)


class EvaluationCenterService:
    runs_path = "evaluation_center/eval_runs.jsonl"

    def __init__(
        self,
        storage: StorageService,
        *,
        dataset_registry_path: str | Path | None = None,
        reports_root: str | Path | None = None,
    ) -> None:
        self.storage = storage
        self.dataset_registry = DatasetRegistryService(
            dataset_registry_path
            or PROJECT_ROOT / "examples" / "datasets" / "dataset_registry.json"
        )
        self.metric_registry = MetricRegistryService()
        self.reports_root = Path(reports_root or PROJECT_ROOT / "reports").resolve()

    def list_datasets(self) -> list[DatasetRegistryItem]:
        return self.dataset_registry.list_datasets()

    def list_metrics(self) -> list[MetricDefinition]:
        return self.metric_registry.list_metrics()

    def register_run(
        self,
        *,
        dataset_id: str,
        eval_type: str,
        metrics: dict[str, Any],
        report_paths: dict[str, str],
        git_commit: str,
    ) -> EvaluationRun:
        gates = self.metric_registry.evaluate(metrics)
        failed = [gate for gate in gates if not gate.passed]
        run = EvaluationRun(
            run_id=new_id("eval"),
            created_at=datetime.now(UTC).isoformat(),
            git_commit=git_commit,
            dataset_id=dataset_id,
            eval_type=eval_type,
            metrics=metrics,
            passed=not failed,
            failed_gates=failed,
            report_paths=report_paths,
        )
        self._append_run(run)
        return run

    def register_from_report(
        self,
        *,
        dataset_id: str,
        eval_type: str,
        report_paths: dict[str, str],
        git_commit: str,
    ) -> EvaluationRun:
        report_path = report_paths.get("json")
        if not report_path:
            raise ValueError("json report path is required when metrics are omitted")
        metrics = self._read_report_metrics(report_path)
        return self.register_run(
            dataset_id=dataset_id,
            eval_type=eval_type,
            metrics=metrics,
            report_paths=report_paths,
            git_commit=git_commit,
        )

    def list_runs(self) -> list[EvaluationRun]:
        try:
            text = self.storage.read_text(self.runs_path)
        except FileNotFoundError:
            return []
        return [
            EvaluationRun.model_validate(json.loads(line))
            for line in text.splitlines()
            if line.strip()
        ]

    def get_run(self, run_id: str) -> EvaluationRun:
        for run in self.list_runs():
            if run.run_id == run_id:
                return run
        raise LookupError("evaluation run not found")

    def resolve_report_path(self, run_id: str, report_key: str) -> Path:
        report_path = self.get_run(run_id).report_paths.get(report_key)
        if not report_path:
            raise LookupError("evaluation report not found")
        resolved = self._resolve_report_path(report_path)
        if not resolved.is_file():
            raise LookupError("evaluation report not found")
        return resolved

    def scorecard(self) -> EvaluationScorecard:
        runs = self.list_runs()
        latest_metrics: dict[str, Any] = {}
        for run in runs:
            latest_metrics.update(run.metrics)
        gates = self.metric_registry.evaluate(latest_metrics)
        failed = [gate for gate in gates if not gate.passed]
        generated_at = datetime.now(UTC).isoformat()
        return EvaluationScorecard(
            run_count=len(runs),
            metrics=latest_metrics,
            passed=not failed,
            failed_gates=failed,
            summary=EvaluationScorecardSummary(
                status="failed" if failed else "passed",
                generated_at=generated_at,
                gates_passed=len(gates) - len(failed),
                gates_total=len(gates),
            ),
            cards=[
                self._scorecard_metric(config, latest_metrics)
                for config in SCORECARD_METRICS
            ],
            warnings=[
                (
                    "Package verification does not imply every target field "
                    "passes strict semantic validation."
                ),
                (
                    "LLM suggestions and Schema Drafts never activate "
                    "production rules automatically."
                ),
                (
                    "Lineage proves traceability and decision history; it does not "
                    "by itself prove strict semantic correctness."
                ),
            ],
        )

    @staticmethod
    def _scorecard_metric(
        config: dict[str, Any],
        metrics: dict[str, Any],
    ) -> EvaluationMetricCard:
        metric_id = str(config["metric_id"])
        value = metrics.get(metric_id)
        target = config["target"]
        passed = False
        if isinstance(value, int | float) and isinstance(target, int | float):
            if config["direction"] == "lower":
                passed = value <= target
            else:
                passed = value >= target
        status = (
            "passed"
            if passed
            else "failed"
            if config["hard_gate"] and value is not None
            else "needs_attention"
        )
        return EvaluationMetricCard(
            metric_id=metric_id,
            name=str(config["name"]),
            value=value,
            target=target,
            status=status,
            explanation=str(config["explanation"]),
        )

    def _append_run(self, run: EvaluationRun) -> None:
        try:
            current = self.storage.read_text(self.runs_path)
        except FileNotFoundError:
            current = ""
        line = json.dumps(run.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        self.storage.write_text(self.runs_path, current + line + "\n")

    def _read_report_metrics(self, report_path: str) -> dict[str, Any]:
        resolved = self._resolve_report_path(report_path)
        payload = json.loads(resolved.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("evaluation report must be a JSON object")
        return {
            key: value
            for key, value in payload.items()
            if isinstance(value, str | int | float | bool)
        }

    def _resolve_report_path(self, report_path: str) -> Path:
        candidate = Path(report_path)
        if candidate.parts and candidate.parts[0].lower() == "reports":
            candidate = Path(*candidate.parts[1:])
        resolved = (self.reports_root / candidate).resolve()
        if self.reports_root != resolved and self.reports_root not in resolved.parents:
            raise ValueError("unsafe report path")
        return resolved
