import { useEffect, useMemo, useState } from "react";

import { api } from "../../api";
import { formatStatus } from "../../app/format";
import { navigate } from "../../app/router";
import { PageState } from "../../components/feedback/PageState";
import { StatusBadge } from "../../components/status/StatusBadge";
import { DataTable } from "../../components/tables/DataTable";
import type { TaskListItem } from "../../types";

const pageSize = 10;
const apiPageSize = 100;

type SortKey = "task_id" | "doc_id" | "schema_id" | "template_id" | "status";

function compareText(left: string, right: string) {
  return left.localeCompare(right, "zh-CN", { numeric: true, sensitivity: "base" });
}

async function listAllTasks() {
  const firstPage = await api.listTasks(1, apiPageSize);
  const items = [...firstPage.items];

  for (let page = 2; items.length < firstPage.total; page += 1) {
    const nextPage = await api.listTasks(page, apiPageSize);
    if (!nextPage.items.length) {
      throw new Error("任务列表分页数据不完整。");
    }
    items.push(...nextPage.items);
  }

  return { items, total: firstPage.total };
}

export function TasksPage() {
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [serverTotal, setServerTotal] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [schemaPackFilter, setSchemaPackFilter] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("task_id");
  const [ascending, setAscending] = useState(true);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const result = await listAllTasks();
      setTasks(result.items);
      setServerTotal(typeof result.total === "number" ? result.total : null);
      setPage(1);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "任务列表读取失败。");
    } finally {
      setLoading(false);
    }
  }

  const statuses = useMemo(
    () => Array.from(new Set(tasks.map((task) => task.status))).sort(compareText),
    [tasks]
  );
  const schemaPacks = useMemo(
    () =>
      Array.from(new Set(tasks.map((task) => `${task.schema_id} / ${task.template_id}`))).sort(
        compareText
      ),
    [tasks]
  );
  const filteredTasks = useMemo(() => {
    const term = search.trim().toLocaleLowerCase();
    return tasks
      .filter((task) => {
        const matchesSearch = !term || [
          task.task_id,
          task.doc_id,
          task.schema_id,
          task.template_id,
          task.status
        ].some((value) => value.toLocaleLowerCase().includes(term));
        const matchesStatus = statusFilter === "all" || task.status === statusFilter;
        const matchesSchemaPack =
          schemaPackFilter === "all" ||
          `${task.schema_id} / ${task.template_id}` === schemaPackFilter;
        return matchesSearch && matchesStatus && matchesSchemaPack;
      })
      .sort((left, right) => {
        const result = compareText(left[sortKey], right[sortKey]);
        return ascending ? result : -result;
      });
  }, [ascending, schemaPackFilter, search, sortKey, statusFilter, tasks]);
  const pageCount = Math.max(1, Math.ceil(filteredTasks.length / pageSize));
  const currentPage = Math.min(page, pageCount);
  const visibleTasks = filteredTasks.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  function updateFilter(update: () => void) {
    update();
    setPage(1);
  }

  return (
    <section className="route-placeholder operations-page tasks-page" aria-labelledby="tasks-title">
      <p className="page-eyebrow">任务</p>
      <h1 id="tasks-title">转换任务</h1>
      <p className="route-placeholder-description">在本地筛选、排序并打开已有转换任务。</p>

      <div className="operations-filter-bar tasks-filter-bar">
        <label>
          搜索任务
          <input
            aria-label="搜索任务"
            value={search}
            onChange={(event) => updateFilter(() => setSearch(event.target.value))}
            placeholder="任务、文档、Schema 或模板"
          />
        </label>
        <label>
          状态
          <select
            value={statusFilter}
            onChange={(event) => updateFilter(() => setStatusFilter(event.target.value))}
          >
            <option value="all">全部状态</option>
            {statuses.map((status) => <option key={status} value={status}>{formatStatus(status)}</option>)}
          </select>
        </label>
        <label>
          SchemaPack
          <select
            value={schemaPackFilter}
            onChange={(event) => updateFilter(() => setSchemaPackFilter(event.target.value))}
          >
            <option value="all">全部 SchemaPack</option>
            {schemaPacks.map((schemaPack) => (
              <option key={schemaPack} value={schemaPack}>{schemaPack}</option>
            ))}
          </select>
        </label>
        <label>
          排序字段
          <select value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}>
            <option value="task_id">任务</option>
            <option value="doc_id">文档</option>
            <option value="schema_id">Schema</option>
            <option value="template_id">模板</option>
            <option value="status">状态</option>
          </select>
        </label>
        <button type="button" onClick={() => setAscending((value) => !value)}>
          {ascending ? "升序" : "降序"}
        </button>
        <button type="button" onClick={() => void load()} disabled={loading}>刷新</button>
      </div>

      {loading ? <PageState kind="loading" title="正在读取任务" /> : null}
      {error ? <PageState kind="error" title="任务列表读取失败" detail={error} /> : null}
      {!loading && !error && !tasks.length ? (
        <PageState kind="empty" title="暂无转换任务" detail="可从“新建转换”创建首个任务。" />
      ) : null}
      {!loading && !error && tasks.length && !filteredTasks.length ? (
        <PageState kind="empty" title="没有匹配的任务" detail="请调整搜索或筛选条件。" />
      ) : null}

      {!loading && !error && visibleTasks.length ? (
        <>
          <DataTable className="tasks-table" label="转换任务表">
            <table>
              <thead>
                <tr>
                  <th>任务</th>
                  <th>文档</th>
                  <th>Schema</th>
                  <th>模板</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {visibleTasks.map((task) => (
                  <tr key={task.task_id}>
                    <td>{task.task_id}</td>
                    <td>{task.doc_id}</td>
                    <td>{task.schema_id}</td>
                    <td>{task.template_id}</td>
                    <td><StatusBadge status={task.status} /></td>
                    <td>
                      <button
                        type="button"
                        aria-label={`打开 ${task.task_id}`}
                        onClick={() => navigate(`/tasks/${encodeURIComponent(task.task_id)}`)}
                      >
                        打开
                      </button>
                      <span>请在任务详情完成验证后下载 Package</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </DataTable>
          <div className="operations-pagination tasks-pagination" aria-label="任务分页">
            <span>服务端任务数：{serverTotal ?? "—"}</span>
            <span>筛选结果：{filteredTasks.length}</span>
            <button type="button" onClick={() => setPage((value) => value - 1)} disabled={currentPage <= 1}>
              上一页
            </button>
            <span>第 {currentPage} / {pageCount} 页</span>
            <button type="button" onClick={() => setPage((value) => value + 1)} disabled={currentPage >= pageCount}>
              下一页
            </button>
          </div>
          <div className="operations-actions tasks-unavailable-actions">
            <button type="button" disabled title="当前 API 不支持重放任务">重放</button>
            <button type="button" disabled title="当前 API 不支持重新验证任务">重新验证</button>
            <span>重放与重新验证当前 API 不支持。</span>
          </div>
        </>
      ) : null}
    </section>
  );
}
