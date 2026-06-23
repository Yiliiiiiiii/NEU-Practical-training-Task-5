import { ListRestart, RotateCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import type { TaskListItem } from "../api/types";
import type { ToastInput, WorkbenchSelection } from "../appTypes";
import { StatusBadge } from "../components/StatusBadge";

interface TasksPageProps {
  selectedTaskId: string | null;
  onSelectTask: (selection: WorkbenchSelection) => void;
  onToast?: (toast: ToastInput) => void;
}

export function TasksPage({ selectedTaskId, onSelectTask, onToast }: TasksPageProps) {
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadTasks = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.listTasks();
      setTasks(response.items);
    } catch (error) {
      onToast?.({
        tone: "danger",
        title: "Task 列表加载失败",
        detail: error instanceof Error ? error.message : "Task 列表加载异常。",
      });
    } finally {
      setIsLoading(false);
    }
  }, [onToast]);

  useEffect(() => {
    void loadTasks();
  }, [loadTasks]);

  function handleOpenTask(task: TaskListItem) {
    onSelectTask({
      docId: task.doc_id,
      schemaId: task.schema_id,
      templateId: task.template_id,
      taskId: task.task_id,
      taskStatus: task.status,
    });
    onToast?.({
      tone: "info",
      title: "已选择 Task",
      detail: task.task_id,
    });
  }

  return (
    <section className="document-panel" aria-labelledby="tasks-page-title">
      <div className="document-panel__header">
        <div>
          <span className="section-label">Task 注册表</span>
          <h2 id="tasks-page-title">Task 列表</h2>
          <p>打开已有转换 Task，并从 Mapping 阶段继续审核。</p>
        </div>
        <button className="secondary-button" disabled={isLoading} onClick={loadTasks} type="button">
          <RotateCw aria-hidden="true" size={15} />
          {isLoading ? "加载中..." : "刷新 Task"}
        </button>
      </div>

      {tasks.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Task</th>
                <th>文档</th>
                <th>Schema</th>
                <th>Template</th>
                <th>状态</th>
                <th>打开</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.task_id}>
                  <td>
                    <strong>{task.task_id}</strong>
                    {task.task_id === selectedTaskId ? <small>当前选择</small> : null}
                  </td>
                  <td>{task.doc_id}</td>
                  <td>{task.schema_id}</td>
                  <td>{task.template_id}</td>
                  <td>
                    <StatusBadge status={task.status} />
                  </td>
                  <td>
                    <button
                      className="secondary-button"
                      onClick={() => handleOpenTask(task)}
                      type="button"
                    >
                      <ListRestart aria-hidden="true" size={15} />
                      打开
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <strong>暂无 Task。</strong>
          <span>可先从导入页创建，也可刷新查看其他客户端创建的 Task。</span>
        </div>
      )}
    </section>
  );
}
