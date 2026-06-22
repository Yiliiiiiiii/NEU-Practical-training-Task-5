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
        title: "Task list failed",
        detail: error instanceof Error ? error.message : "Unexpected task list failure.",
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
      title: "Task selected",
      detail: task.task_id,
    });
  }

  return (
    <section className="document-panel" aria-labelledby="tasks-page-title">
      <div className="document-panel__header">
        <div>
          <span className="section-label">Task registry</span>
          <h2 id="tasks-page-title">Tasks</h2>
          <p>Open an existing conversion task and continue review from the mapping stage.</p>
        </div>
        <button className="secondary-button" disabled={isLoading} onClick={loadTasks} type="button">
          <RotateCw aria-hidden="true" size={15} />
          {isLoading ? "Loading..." : "Refresh tasks"}
        </button>
      </div>

      {tasks.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Task</th>
                <th>Document</th>
                <th>Schema</th>
                <th>Template</th>
                <th>Status</th>
                <th>Open</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.task_id}>
                  <td>
                    <strong>{task.task_id}</strong>
                    {task.task_id === selectedTaskId ? <small>Current selection</small> : null}
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
                      Open
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <strong>No tasks loaded.</strong>
          <span>Create one from Import, or refresh after another client has created tasks.</span>
        </div>
      )}
    </section>
  );
}
