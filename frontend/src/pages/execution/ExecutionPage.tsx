import { useEffect, useState } from "react";

import { api } from "../../api";
import { formatStatus } from "../../app/format";
import { PageState } from "../../components/feedback/PageState";
import { StatusBadge } from "../../components/status/StatusBadge";
import type { TaskDetailResponse } from "../../types";

const stages = ["输入", "字段映射", "转换", "元数据", "内容组织", "验证", "一致性", "打包", "校验"];

export function ExecutionPage({ taskId }: { taskId: string }) {
  const [task, setTask] = useState<TaskDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    void api.getTask(taskId)
      .then((result) => {
        if (active) setTask(result);
      })
      .catch((caught) => {
        if (active) setError(caught instanceof Error ? caught.message : "任务读取失败。");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [taskId]);

  return (
    <section className="route-placeholder execution-page" aria-labelledby="execution-title">
      <p className="page-eyebrow">转换</p>
      <h1 id="execution-title">执行转换</h1>
      <p className="route-placeholder-description">
        当前 API 为同步执行，不提供实时阶段事件；下方仅显示服务端返回的任务终态或待复核状态。
      </p>

      {loading ? <PageState kind="loading" title="正在读取任务结果" /> : null}
      {error ? <PageState kind="error" title="任务结果读取失败" detail={error} /> : null}
      {task ? (
        <>
          <section className="execution-page-result" aria-labelledby="execution-result-title">
            <h2 id="execution-result-title">任务结果</h2>
            <dl>
              <div><dt>任务</dt><dd>{task.task_id}</dd></div>
              <div><dt>状态</dt><dd><StatusBadge status={task.status} /></dd></div>
              <div><dt>结果说明</dt><dd>{formatStatus(task.status)}</dd></div>
            </dl>
          </section>
          <section className="execution-page-stages" aria-labelledby="execution-stages-title">
            <h2 id="execution-stages-title">固定执行阶段</h2>
            <ol>
              {stages.map((stage) => <li key={stage}>{stage}</li>)}
            </ol>
          </section>
        </>
      ) : null}
    </section>
  );
}
