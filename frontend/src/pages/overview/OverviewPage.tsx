import { useEffect, useState } from "react";

import { api } from "../../api";
import { formatStatus } from "../../app/format";
import { navigate } from "../../app/router";
import { PageState } from "../../components/feedback/PageState";
import type { EvaluationScorecard, ReviewWorkbenchSummary, TaskListItem } from "../../types";

type LoadState = "loading" | "available" | "unavailable";

function stateLabel(state: LoadState) {
  if (state === "available") return "可访问";
  if (state === "unavailable") return "不可访问";
  return "读取中";
}

export function OverviewPage() {
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [taskTotal, setTaskTotal] = useState<number | null>(null);
  const [reviewSummary, setReviewSummary] = useState<ReviewWorkbenchSummary | null>(null);
  const [scorecard, setScorecard] = useState<EvaluationScorecard | null>(null);
  const [taskState, setTaskState] = useState<LoadState>("loading");
  const [reviewState, setReviewState] = useState<LoadState>("loading");
  const [evaluationState, setEvaluationState] = useState<LoadState>("loading");

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setTaskState("loading");
    setReviewState("loading");
    setEvaluationState("loading");
    const [taskResult, reviewResult, evaluationResult] = await Promise.allSettled([
      api.listTasks(1, 5),
      api.getReviewSummary(),
      api.getEvaluationScorecard()
    ]);

    if (taskResult.status === "fulfilled") {
      setTasks(taskResult.value.items);
      setTaskTotal(
        typeof taskResult.value.total === "number" ? taskResult.value.total : null
      );
      setTaskState("available");
    } else {
      setTaskState("unavailable");
    }

    if (reviewResult.status === "fulfilled") {
      setReviewSummary(reviewResult.value);
      setReviewState("available");
    } else {
      setReviewState("unavailable");
    }

    if (evaluationResult.status === "fulfilled") {
      setScorecard(evaluationResult.value);
      setEvaluationState("available");
    } else {
      setEvaluationState("unavailable");
    }
  }

  const hasUnavailableSource = [taskState, reviewState, evaluationState].includes("unavailable");
  const evidenceGate =
    evaluationState === "available"
      ? scorecard?.passed
        ? "通过"
        : "未通过"
      : "—";

  return (
    <section className="route-placeholder operations-page overview-page" aria-labelledby="overview-title">
      <p className="page-eyebrow">概览</p>
      <h1 id="overview-title">工作概览</h1>
      <p className="route-placeholder-description">
        查看本地转换任务、待复核项和证据门状态。
      </p>
      <p>
        <a
          className="operations-primary-link"
          href="/conversions/new"
          onClick={(event) => {
            event.preventDefault();
            navigate("/conversions/new");
          }}
        >
          新建转换
        </a>
      </p>

      {hasUnavailableSource ? (
        <PageState
          kind="partial"
          title="部分概览数据暂不可用"
          detail="已保留可读取的数据；请在服务恢复后刷新。"
        />
      ) : null}

      <section className="operations-section overview-recent-tasks" aria-labelledby="overview-tasks-title">
        <h2 id="overview-tasks-title">最近任务</h2>
        {taskState === "loading" ? <PageState kind="loading" /> : null}
        {taskState === "available" && !tasks.length ? (
          <PageState kind="empty" title="暂无转换任务" />
        ) : null}
        {tasks.length ? (
          <table>
            <thead>
              <tr>
                <th>任务</th>
                <th>SchemaPack</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.task_id}>
                  <td>
                    <a
                      href={`/tasks/${encodeURIComponent(task.task_id)}`}
                      onClick={(event) => {
                        event.preventDefault();
                        navigate(`/tasks/${encodeURIComponent(task.task_id)}`);
                      }}
                    >
                      {task.task_id}
                    </a>
                  </td>
                  <td>{task.schema_id} / {task.template_id}</td>
                  <td>{formatStatus(task.status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        <p>服务端任务数：{taskTotal ?? "—"}</p>
      </section>

      <section className="operations-section overview-operational-state" aria-labelledby="overview-state-title">
        <h2 id="overview-state-title">本地服务状态</h2>
        <dl>
          <div><dt>任务服务</dt><dd>{stateLabel(taskState)}</dd></div>
          <div><dt>复核服务</dt><dd>{stateLabel(reviewState)}</dd></div>
          <div><dt>评测服务</dt><dd>{stateLabel(evaluationState)}</dd></div>
          <div><dt>待复核</dt><dd>{reviewSummary?.pending ?? "—"}</dd></div>
          <div><dt>证据门</dt><dd>{evidenceGate}</dd></div>
        </dl>
      </section>

      <p>
        <button type="button" onClick={() => void load()}>刷新概览</button>
      </p>
    </section>
  );
}
