import { useEffect, useRef, useState } from "react";

import { api } from "../../api";
import { formatStatus } from "../../app/format";
import { PageState } from "../../components/feedback/PageState";
import { StatusBadge } from "../../components/status/StatusBadge";
import type { TaskExecuteResponse } from "../../types";

export function ExecutionPage({ taskId }: { taskId: string }) {
  const [result, setResult] = useState<TaskExecuteResponse | null>(null);
  const [executing, setExecuting] = useState(true);
  const [error, setError] = useState("");
  const executionRequest = useRef<{ taskId: string; promise: Promise<TaskExecuteResponse> } | null>(null);

  useEffect(() => {
    let active = true;
    setResult(null);
    setExecuting(true);
    setError("");
    if (executionRequest.current?.taskId !== taskId) {
      executionRequest.current = { taskId, promise: api.executeTask(taskId) };
    }
    void executionRequest.current.promise
      .then((result) => {
        if (active) setResult(result);
      })
      .catch((caught) => {
        if (active) setError(caught instanceof Error ? caught.message : "转换执行失败。");
      })
      .finally(() => {
        if (active) setExecuting(false);
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
              <div><dt>待复核项</dt><dd>{result.review_required_count}</dd></div>
              <div><dt>未映射必填项</dt><dd>{result.unmapped_required_count}</dd></div>
            </dl>
          </section>
          <a href={`/tasks/${encodeURIComponent(result.task_id)}`}>查看任务详情</a>
        </>
      ) : null}
    </section>
  );
}
