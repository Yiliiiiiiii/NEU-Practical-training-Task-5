from typing import Any, Literal

from pydantic import Field

from app.schemas.common import StrictBaseModel


class DatasetRegistryItem(StrictBaseModel):
    dataset_id: str
    dataset_type: str
    doc_count: int
    doc_types: dict[str, int] = Field(default_factory=dict)
    gold_files: list[str] = Field(default_factory=list)


class DatasetRegistryResponse(StrictBaseModel):
    items: list[DatasetRegistryItem]


class MetricDefinition(StrictBaseModel):
    metric_id: str
    description: str
    higher_is_better: bool
    threshold: float | int | bool | None = None
    gate_op: str | None = None


class MetricRegistryResponse(StrictBaseModel):
    items: list[MetricDefinition]


class RegressionGateResult(StrictBaseModel):
    metric: str
    op: str
    expected: float | int | bool
    actual: float | int | bool | None
    passed: bool


class EvaluationRun(StrictBaseModel):
    run_id: str
    created_at: str
    git_commit: str
    dataset_id: str
    eval_type: str
    metrics: dict[str, Any]
    passed: bool
    failed_gates: list[RegressionGateResult] = Field(default_factory=list)
    report_paths: dict[str, str] = Field(default_factory=dict)


class EvaluationRunRequest(StrictBaseModel):
    dataset_id: str
    eval_type: str
    git_commit: str = "unknown"
    metrics: dict[str, Any] = Field(default_factory=dict)
    report_paths: dict[str, str] = Field(default_factory=dict)


class EvaluationRunListResponse(StrictBaseModel):
    items: list[EvaluationRun]
    total: int


class EvaluationScorecardSummary(StrictBaseModel):
    status: Literal["passed", "needs_attention", "failed"]
    generated_at: str
    gates_passed: int
    gates_total: int


class EvaluationMetricCard(StrictBaseModel):
    metric_id: str
    name: str
    value: Any | None = None
    target: float | int | bool
    status: Literal["passed", "needs_attention", "failed"]
    explanation: str


class EvaluationScorecard(StrictBaseModel):
    run_count: int
    metrics: dict[str, Any]
    passed: bool
    failed_gates: list[RegressionGateResult] = Field(default_factory=list)
    summary: EvaluationScorecardSummary
    cards: list[EvaluationMetricCard] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
