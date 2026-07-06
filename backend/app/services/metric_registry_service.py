from app.schemas.evaluation_center import MetricDefinition, RegressionGateResult


class MetricRegistryService:
    METRICS = [
        MetricDefinition(
            metric_id="adapter_validation_pass_rate",
            description="Share of adapter outputs that validate as standard UIR.",
            higher_is_better=True,
        ),
        MetricDefinition(
            metric_id="adapter_trace_coverage",
            description="Share of generated blocks with source trace evidence.",
            higher_is_better=True,
            threshold=0.95,
            gate_op=">=",
        ),
        MetricDefinition(
            metric_id="schema_router_top1_accuracy",
            description="Top-1 schema routing accuracy.",
            higher_is_better=True,
        ),
        MetricDefinition(
            metric_id="mapping_recall",
            description="Gold mappings covered by safe mappings.",
            higher_is_better=True,
            threshold=0.55,
        ),
        MetricDefinition(
            metric_id="required_field_coverage",
            description="Coverage of required schema fields.",
            higher_is_better=True,
        ),
        MetricDefinition(
            metric_id="review_required_count",
            description="Mappings requiring human review.",
            higher_is_better=False,
        ),
        MetricDefinition(
            metric_id="required_missing_count",
            description="Required fields still missing.",
            higher_is_better=False,
        ),
        MetricDefinition(
            metric_id="badcase_violation_count",
            description="Forbidden badcase mappings that escaped protection.",
            higher_is_better=False,
            threshold=0,
            gate_op="==",
        ),
        MetricDefinition(
            metric_id="package_verification_rate",
            description="Share of packages passing verification.",
            higher_is_better=True,
            threshold=1.0,
            gate_op=">=",
        ),
        MetricDefinition(
            metric_id="retrieval_recall_at_3",
            description="Retrieval recall at three results.",
            higher_is_better=True,
        ),
        MetricDefinition(
            metric_id="summary_faithfulness_score",
            description="Summary faithfulness score.",
            higher_is_better=True,
        ),
        MetricDefinition(
            metric_id="tag_quality_score",
            description="Content tag quality score.",
            higher_is_better=True,
        ),
        MetricDefinition(
            metric_id="downstream_contract_pass_rate",
            description="Downstream consumer contract pass rate.",
            higher_is_better=True,
        ),
        MetricDefinition(
            metric_id="llm_auto_accepted_count",
            description="LLM suggestions accepted without human review.",
            higher_is_better=False,
            threshold=0,
            gate_op="==",
        ),
        MetricDefinition(
            metric_id="secret_leak_count",
            description="Secrets found in reports or artifacts.",
            higher_is_better=False,
            threshold=0,
            gate_op="==",
        ),
        MetricDefinition(
            metric_id="old_snapshot_unchanged",
            description="Whether historical task snapshots remain unchanged.",
            higher_is_better=True,
            threshold=True,
            gate_op="==",
        ),
        MetricDefinition(
            metric_id="lineage_parse_pass_rate",
            description="Share of lineage graphs that parse against the versioned schema.",
            higher_is_better=True,
            threshold=1.0,
            gate_op=">=",
        ),
        MetricDefinition(
            metric_id="lineage_broken_edges",
            description="Lineage edges whose source or target node is missing.",
            higher_is_better=False,
            threshold=0,
            gate_op="==",
        ),
        MetricDefinition(
            metric_id="lineage_secret_leaks",
            description="Secret-like keys or values exposed by lineage artifacts.",
            higher_is_better=False,
            threshold=0,
            gate_op="==",
        ),
        MetricDefinition(
            metric_id="lineage_field_coverage",
            description="Share of target schema fields with a traceable mapping path.",
            higher_is_better=True,
            threshold=0.9,
            gate_op=">=",
        ),
        MetricDefinition(
            metric_id="lineage_chunk_coverage",
            description="Share of chunks linked to source UIR blocks.",
            higher_is_better=True,
        ),
        MetricDefinition(
            metric_id="lineage_artifact_coverage",
            description="Share of package manifest entries linked to rendered artifacts.",
            higher_is_better=True,
        ),
    ]

    def list_metrics(self) -> list[MetricDefinition]:
        return list(self.METRICS)

    def evaluate(self, metrics: dict) -> list[RegressionGateResult]:
        results: list[RegressionGateResult] = []
        for definition in self.METRICS:
            if definition.gate_op is None or definition.threshold is None:
                continue
            if definition.metric_id not in metrics:
                continue
            actual = metrics[definition.metric_id]
            passed = self._compare(actual, definition.gate_op, definition.threshold)
            results.append(
                RegressionGateResult(
                    metric=definition.metric_id,
                    op=definition.gate_op,
                    expected=definition.threshold,
                    actual=actual,
                    passed=passed,
                )
            )
        return results

    @staticmethod
    def _compare(actual, op: str, expected) -> bool:
        if op == "==":
            return actual == expected
        if op == ">=":
            return actual >= expected
        if op == "<=":
            return actual <= expected
        raise ValueError(f"unsupported gate operator: {op}")
