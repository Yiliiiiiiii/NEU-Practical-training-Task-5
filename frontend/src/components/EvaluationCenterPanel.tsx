import {
  BarChart3,
  CheckCircle2,
  Database,
  ExternalLink,
  ListChecks,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  ShieldX
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { api } from "../api";
import type {
  EvaluationDataset,
  EvaluationMetricDefinition,
  EvaluationRun,
  EvaluationScorecard
} from "../types";

type EvaluationStatus = "passed" | "needs_attention" | "failed";

const statusLabels: Record<EvaluationStatus, string> = {
  passed: "通过",
  needs_attention: "需关注",
  failed: "失败"
};

export function EvaluationCenterPanel() {
  const [datasets, setDatasets] = useState<EvaluationDataset[]>([]);
  const [definitions, setDefinitions] = useState<EvaluationMetricDefinition[]>([]);
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [scorecard, setScorecard] = useState<EvaluationScorecard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void load();
  }, []);

  const gateRows = useMemo(
    () =>
      definitions
        .filter(
          (item) =>
            item.gate_op &&
            item.threshold !== null &&
            item.threshold !== undefined
        )
        .map((definition) => {
          const value = scorecard?.metrics[definition.metric_id];
          return {
            definition,
            value,
            status: gateStatus(definition, value)
          };
        }),
    [definitions, scorecard]
  );

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [datasetResult, metricResult, runResult, scorecardResult] =
        await Promise.all([
          api.listEvaluationDatasets(),
          api.listEvaluationMetrics(),
          api.listEvaluationRuns(),
          api.getEvaluationScorecard()
        ]);
      setDatasets(datasetResult.items);
      setDefinitions(metricResult.items);
      setRuns(runResult.items);
      setScorecard(scorecardResult);
    } catch (caught) {
      const detail =
        caught instanceof Error ? caught.message : "Evaluation Center 请求失败";
      setError(detail);
    } finally {
      setLoading(false);
    }
  }

  const overallStatus = effectiveOverallStatus(scorecard);

  return (
    <div className="governance-panel evaluation-center evaluation-center-v2">
      <header className="evaluation-header">
        <div>
          <div className={`evaluation-status status-${overallStatus}`}>
            <StatusIcon status={overallStatus} />
            <span>回归门：{statusLabels[overallStatus]}</span>
          </div>
          <p>
            集中查看数据集、执行记录、质量指标与安全门。所有状态均提供文字标签，
            不仅依赖颜色。
          </p>
        </div>
        <button
          type="button"
          className="icon-button"
          onClick={() => void load()}
          title="刷新"
          aria-label="刷新评测数据"
          disabled={loading}
        >
          <RefreshCw size={16} />
          {loading ? "加载中" : "刷新"}
        </button>
      </header>

      <div className="evaluation-boundary-note">
        <ShieldAlert size={18} aria-hidden="true" />
        <p>
          <strong>Package verification 证明成果包结构、manifest、hash、JSON/JSONL 可解析和 traceability；</strong>
          不代表所有 target field 都通过 strict semantic validation。
          LLM suggestions 和 Schema Draft 均不会自动激活 production rules。
        </p>
      </div>

      {error ? (
        <div className="evaluation-error" role="alert">
          <strong>评测数据暂时不可用</strong>
          <span>{error}</span>
          <small>请确认后端服务可访问后重新刷新；现有报告文件不受影响。</small>
        </div>
      ) : null}

      <section className="evaluation-section" aria-labelledby="dataset-registry-title">
        <SectionHeading
          id="dataset-registry-title"
          icon={<Database size={17} />}
          title="数据集目录"
          meta={`${datasets.length} 个数据集`}
        />
        <div className="evaluation-table" role="table" aria-label="数据集目录">
          <div className="evaluation-table-head" role="row">
            <span>数据集</span>
            <span>类型</span>
            <span>规模</span>
            <span>最近执行</span>
            <span>证据</span>
          </div>
          {datasets.map((dataset) => {
            const latestRun = [...runs]
              .reverse()
              .find((run) => run.dataset_id === dataset.dataset_id);
            return (
              <div className="evaluation-table-row" role="row" key={dataset.dataset_id}>
                <strong>{dataset.dataset_id}</strong>
                <span>{dataset.dataset_type}</span>
                <span>
                  {dataset.doc_count}{" "}
                  {dataset.dataset_type.includes("external") ? "样本" : "文档"}
                </span>
                <time>
                  {latestRun ? formatDate(latestRun.created_at) : "尚未登记"}
                </time>
                <span className="evaluation-evidence-count">
                  {dataset.gold_files.length} 个路径
                </span>
              </div>
            );
          })}
          {!datasets.length ? (
            <p className="evaluation-empty">暂无已登记数据集。</p>
          ) : null}
        </div>
      </section>

      <section className="evaluation-section" aria-labelledby="evaluation-runs-title">
        <SectionHeading
          id="evaluation-runs-title"
          icon={<ListChecks size={17} />}
          title="评测运行"
          meta={`${runs.length} 次执行`}
        />
        <div className="evaluation-run-list">
          {[...runs].reverse().slice(0, 6).map((run) => (
            <article className="evaluation-run-item" key={run.run_id}>
              <StatusBadge status={run.passed ? "passed" : "failed"} />
              <div>
                <strong>{run.eval_type}</strong>
                <span>{run.run_id}</span>
              </div>
              <dl>
                <div>
                  <dt>数据集</dt>
                  <dd>{run.dataset_id}</dd>
                </div>
                <div>
                  <dt>执行时间</dt>
                  <dd>{formatDate(run.created_at)}</dd>
                </div>
                <div>
                  <dt>Package</dt>
                  <dd>{formatMetric(run.metrics.package_verification_rate)}</dd>
                </div>
                <div>
                  <dt>Badcase / LLM</dt>
                  <dd>
                    {formatMetric(run.metrics.badcase_violation_count)} /{" "}
                    {formatMetric(run.metrics.llm_auto_accepted_count)}
                  </dd>
                </div>
              </dl>
              <span className="evaluation-report-links">
                {Object.keys(run.report_paths).map((reportKey) => (
                  <a
                    href={api.evaluationReportUrl(run.run_id, reportKey)}
                    target="_blank"
                    rel="noreferrer"
                    key={reportKey}
                    title={`打开 ${reportKey} 报告`}
                  >
                    {reportKey}
                    <ExternalLink size={12} />
                  </a>
                ))}
              </span>
            </article>
          ))}
          {!runs.length ? (
            <p className="evaluation-empty">暂无已登记执行记录。</p>
          ) : null}
        </div>
      </section>

      <section className="evaluation-section" aria-labelledby="metric-scorecard-title">
        <SectionHeading
          id="metric-scorecard-title"
          icon={<BarChart3 size={17} />}
          title="指标记分卡"
          meta={`${scorecard?.cards.length ?? 0} 项指标`}
        />
        <div className="evaluation-card-grid">
          {scorecard?.cards.map((card) => {
            const status = effectiveCardStatus(card);
            return (
              <article className={`evaluation-card status-${status}`} key={card.metric_id}>
                <div>
                  <strong>{card.name}</strong>
                  <StatusBadge status={status} />
                </div>
                <p>
                  <span>{formatMetric(card.value)}</span>
                  <small>目标 {formatTarget(card.metric_id, card.target)}</small>
                </p>
                <em>{card.explanation}</em>
              </article>
            );
          })}
          {!scorecard?.cards.length ? (
            <p className="evaluation-empty">暂无 scorecard 数据。</p>
          ) : null}
        </div>
      </section>

      <section className="evaluation-section" aria-labelledby="regression-gates-title">
        <SectionHeading
          id="regression-gates-title"
          icon={<ShieldCheck size={17} />}
          title="回归门"
          meta={
            scorecard
              ? `${scorecard.summary.gates_passed}/${scorecard.summary.gates_total} 通过`
              : "未报告"
          }
        />
        <div className="evaluation-gates">
          {gateRows.map(({ definition, value, status }) => (
            <div className="evaluation-gate-row" key={definition.metric_id}>
              <StatusBadge status={status} />
              <strong>{definition.metric_id}</strong>
              <span>{formatMetric(value)}</span>
              <code>
                {definition.gate_op} {String(definition.threshold)}
              </code>
              <small>
                {status === "passed"
                  ? "当前值满足安全门"
                  : "当前值未满足阈值，请检查对应报告"}
              </small>
            </div>
          ))}
          {!gateRows.length ? (
            <p className="evaluation-empty">暂无 regression gate 定义。</p>
          ) : null}
        </div>
        <div className="evaluation-reproduction">
          <strong>复现命令</strong>
          <code>
            backend\.venv\Scripts\python.exe scripts\check_regression_gates.py
            --metrics reports\evaluation_center\current_metrics.json --gates
            reports\evaluation_center\regression_gates.json
          </code>
        </div>
      </section>
    </div>
  );
}

function SectionHeading({
  id,
  icon,
  title,
  meta
}: {
  id: string;
  icon: ReactNode;
  title: string;
  meta: string;
}) {
  return (
    <div className="evaluation-section-heading">
      <div>
        {icon}
        <h3 id={id}>{title}</h3>
      </div>
      <span>{meta}</span>
    </div>
  );
}

function StatusBadge({ status }: { status: EvaluationStatus }) {
  return (
    <span className={`evaluation-status-badge status-${status}`}>
      <StatusIcon status={status} />
      {statusLabels[status]}
    </span>
  );
}

function StatusIcon({ status }: { status: EvaluationStatus }) {
  if (status === "passed") {
    return <CheckCircle2 size={14} aria-hidden="true" />;
  }
  if (status === "needs_attention") {
    return <ShieldAlert size={14} aria-hidden="true" />;
  }
  return <ShieldX size={14} aria-hidden="true" />;
}

function effectiveOverallStatus(
  scorecard: EvaluationScorecard | null
): EvaluationStatus {
  if (!scorecard) {
    return "needs_attention";
  }
  if (
    Number(scorecard.metrics.badcase_violation_count ?? 0) > 0 ||
    Number(scorecard.metrics.llm_auto_accepted_count ?? 0) > 0
  ) {
    return "failed";
  }
  return scorecard.summary.status;
}

function effectiveCardStatus(
  card: EvaluationScorecard["cards"][number]
): EvaluationStatus {
  if (
    ["badcase_violation_count", "llm_auto_accepted_count"].includes(
      card.metric_id
    ) &&
    Number(card.value ?? 0) > 0
  ) {
    return "failed";
  }
  return card.status;
}

function gateStatus(
  definition: EvaluationMetricDefinition,
  value: unknown
): EvaluationStatus {
  if (typeof value !== "number" || typeof definition.threshold !== "number") {
    return "failed";
  }
  const passed =
    definition.gate_op === "=="
      ? value === definition.threshold
      : definition.gate_op === ">="
        ? value >= definition.threshold
        : definition.gate_op === "<="
          ? value <= definition.threshold
          : false;
  return passed ? "passed" : "failed";
}

function formatMetric(value: unknown) {
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(3);
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "string" && value) {
    return value;
  }
  return "未报告";
}

function formatTarget(metricId: string, target: number | boolean) {
  const lowerIsBetter = [
    "badcase_violation_count",
    "llm_auto_accepted_count",
    "review_required_count",
    "required_missing_count"
  ].includes(metricId);
  return `${lowerIsBetter ? "≤" : "≥"} ${String(target)}`;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}
