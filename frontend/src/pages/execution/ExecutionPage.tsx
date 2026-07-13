import { useEffect, useRef, useState } from "react";

import { api } from "../../api";
import { formatStatus } from "../../app/format";
import { PageState } from "../../components/feedback/PageState";
import { StatusBadge } from "../../components/status/StatusBadge";
import type { TaskDetailResponse, TaskExecuteResponse } from "../../types";

type ExecutionResult = TaskDetailResponse | TaskExecuteResponse;

function isExecutionResponse(result: ExecutionResult): result is TaskExecuteResponse {
  return "review_required_count" in result;
}

function canExecuteTask(status: string) {
  return status === "created" || status === "pending";
}

export function ExecutionPage({ taskId }: { taskId: string }) {
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState("");
  const executionRequest = useRef<{ taskId: string; promise: Promise<TaskExecuteResponse> } | null>(null);

  useEffect(() => {
    let active = true;
    setResult(null);
    setLoading(true);
    setExecuting(false);
    setError("");
    void api.getTask(taskId)
      .then(async (task) => {
        if (!active) {
          return;
        }
        if (!canExecuteTask(task.status)) {
          setResult(task);
          return;
        }

        setLoading(false);
        setExecuting(true);
        if (executionRequest.current?.taskId !== taskId) {
          executionRequest.current = { taskId, promise: api.executeTask(taskId) };
        }
        const executed = await executionRequest.current.promise;
        if (active) {
          setResult(executed);
        }
      })
      .catch((caught) => {
        if (active) setError(caught instanceof Error ? caught.message : "任务状态读取或转换执行失败。");
      })
      .finally(() => {
        if (active) {
          setLoading(false);
          setExecuting(false);
        }
      });
    return () => { active = false; };
  }, [taskId]);

  return (
    <section className="route-placeholder execution-page" aria-labelledby="execution-title">
      <p className="page-eyebrow">转换</p>
      <h1 id="execution-title">执行转换</h1>
      <p className="route-placeholder-description">
        执行结果由服务端同步返回；页面不会推断或展示未经 API 提供的阶段信息。
      </p>

      {loading ? (
        <PageState
          kind="loading"
          title="正在读取任务状态"
          detail="仅新建或待处理任务会执行转换；已结束任务将展示服务端事实状态。"
        />
      ) : null}
      {executing ? (
        <PageState
          kind="loading"
          title="正在执行转换"
          detail="服务正在同步执行，当前 API 未提供实时阶段事件。"
        />
      ) : null}
      {error ? <PageState kind="error" title="转换执行失败" detail={error} /> : null}
      {result ? (
        <>
          <section className="execution-page-result" aria-labelledby="execution-result-title">
            <h2 id="execution-result-title">任务结果</h2>
            <dl>
              <div><dt>任务</dt><dd>{result.task_id}</dd></div>
              <div><dt>状态</dt><dd><StatusBadge status={result.status} /></dd></div>
              <div><dt>结果说明</dt><dd>{formatStatus(result.status)}</dd></div>
              {isExecutionResponse(result) ? (
                <>
                  <div><dt>待复核项</dt><dd>{result.review_required_count}</dd></div>
                  <div><dt>未映射必填项</dt><dd>{result.unmapped_required_count}</dd></div>
                </>
              ) : null}
            </dl>
          </section>
          <a href={`/tasks/${encodeURIComponent(result.task_id)}`}>查看任务详情</a>
        </>
      ) : null}
    </section>
  );
}
