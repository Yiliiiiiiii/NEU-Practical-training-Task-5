import { Brain, CheckCircle2, Power, RotateCw, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import type {
  JsonObject,
  KnowledgeMetricsResponse,
  KnowledgePackItem,
  LearningCandidateItem,
} from "../api/types";
import type { ToastInput, WorkbenchSelection } from "../appTypes";
import { StatusBadge } from "../components/StatusBadge";

interface KnowledgePageProps {
  selection: WorkbenchSelection;
  onToast?: (toast: ToastInput) => void;
}

const EMPTY_METRICS: KnowledgeMetricsResponse = {
  real_runs: 0,
  pending_candidates: 0,
  approved_candidates: 0,
  rejected_candidates: 0,
  active_packs: 0,
};

function formatJson(value: JsonObject): string {
  const json = JSON.stringify(value);
  return json === "{}" ? "-" : json;
}

export function KnowledgePage({ selection, onToast }: KnowledgePageProps) {
  const [metrics, setMetrics] = useState<KnowledgeMetricsResponse>(EMPTY_METRICS);
  const [candidates, setCandidates] = useState<LearningCandidateItem[]>([]);
  const [packs, setPacks] = useState<KnowledgePackItem[]>([]);
  const [isBusy, setIsBusy] = useState(false);

  const refresh = useCallback(async () => {
    setIsBusy(true);
    try {
      const [metricsResponse, candidateResponse, packResponse] = await Promise.all([
        api.getKnowledgeMetrics(),
        api.listKnowledgeCandidates("pending"),
        api.listKnowledgePacks(),
      ]);
      setMetrics(metricsResponse);
      setCandidates(candidateResponse.items);
      setPacks(packResponse.items);
    } catch (error) {
      onToast?.({
        tone: "danger",
        title: "成长数据加载失败",
        detail: error instanceof Error ? error.message : "请稍后重试。",
      });
    } finally {
      setIsBusy(false);
    }
  }, [onToast]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function runAction(action: () => Promise<void>, failureTitle: string) {
    setIsBusy(true);
    try {
      await action();
    } catch (error) {
      onToast?.({
        tone: "danger",
        title: failureTitle,
        detail: error instanceof Error ? error.message : "知识操作失败。",
      });
    } finally {
      setIsBusy(false);
    }
  }

  async function decideCandidate(candidate: LearningCandidateItem, decision: "approved" | "rejected") {
    await runAction(
      async () => {
        await api.decideKnowledgeCandidate(candidate.candidate_id, {
          decision,
          reviewer: "human",
          final_payload: decision === "approved" ? candidate.proposed_payload : {},
          reason: decision === "approved" ? "人工批准" : "人工拒绝",
        });
        await refresh();
        onToast?.({
          tone: "success",
          title: decision === "approved" ? "候选知识已批准" : "候选知识已拒绝",
          detail: candidate.candidate_id,
        });
      },
      decision === "approved" ? "批准失败" : "拒绝失败",
    );
  }

  async function handleCaptureCurrentTask() {
    if (!selection.taskId) {
      onToast?.({
        tone: "warning",
        title: "请先选择 Task",
        detail: "打开一个 Task 后再沉淀映射知识。",
      });
      return;
    }

    await runAction(async () => {
      const run = await api.captureKnowledgeRun(selection.taskId);
      await api.deriveKnowledgeCandidates(run.real_run_id);
      await refresh();
      onToast?.({
        tone: "success",
        title: "当前 Task 已沉淀",
        detail: run.real_run_id,
      });
    }, "沉淀失败");
  }

  async function handleActivatePack(pack: KnowledgePackItem) {
    await runAction(async () => {
      await api.activateKnowledgePack(pack.pack_id);
      await refresh();
      onToast?.({
        tone: "success",
        title: "知识包已启用",
        detail: pack.name,
      });
    }, "启用知识包失败");
  }

  return (
    <section className="document-panel" aria-labelledby="knowledge-page-title">
      <div className="document-panel__header">
        <div>
          <span className="section-label">受控学习</span>
          <h2 id="knowledge-page-title">映射成长中心</h2>
          <p>从人工复核和失败案例中沉淀候选知识，批准后再进入知识包。</p>
        </div>
        <div className="button-row">
          <button className="secondary-button" disabled={isBusy} onClick={() => void refresh()} type="button">
            <RotateCw aria-hidden="true" size={15} />
            刷新
          </button>
          <button
            className="primary-button"
            disabled={isBusy}
            onClick={() => void handleCaptureCurrentTask()}
            type="button"
          >
            <Brain aria-hidden="true" size={15} />
            沉淀当前 Task
          </button>
        </div>
      </div>

      <div className="metric-row">
        <div className="metric">
          <strong>{metrics.real_runs}</strong>
          <span>真实运行</span>
        </div>
        <div className="metric">
          <strong>{metrics.pending_candidates}</strong>
          <span>待复核</span>
        </div>
        <div className="metric">
          <strong>{metrics.approved_candidates}</strong>
          <span>已批准</span>
        </div>
        <div className="metric">
          <strong>{metrics.active_packs}</strong>
          <span>启用知识包</span>
        </div>
      </div>

      <h3>待复核候选</h3>
      {candidates.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>类型</th>
                <th>目标字段</th>
                <th>风险</th>
                <th>建议载荷</th>
                <th>证据</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => (
                <tr key={candidate.candidate_id}>
                  <td>
                    <strong>{candidate.candidate_type}</strong>
                    <small>{candidate.generator}</small>
                  </td>
                  <td>{candidate.target_field_id ?? "-"}</td>
                  <td>{candidate.risk_level}</td>
                  <td>{formatJson(candidate.proposed_payload)}</td>
                  <td>{formatJson(candidate.evidence)}</td>
                  <td>
                    <div className="button-row">
                      <button
                        className="secondary-button"
                        disabled={isBusy}
                        onClick={() => void decideCandidate(candidate, "approved")}
                        type="button"
                      >
                        <CheckCircle2 aria-hidden="true" size={15} />
                        批准
                      </button>
                      <button
                        className="secondary-button"
                        disabled={isBusy}
                        onClick={() => void decideCandidate(candidate, "rejected")}
                        type="button"
                      >
                        <XCircle aria-hidden="true" size={15} />
                        拒绝
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <strong>暂无待复核候选。</strong>
          <span>可以先沉淀当前 Task，或刷新查看其他客户端生成的候选。</span>
        </div>
      )}

      <h3>知识包</h3>
      {packs.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>范围</th>
                <th>状态</th>
                <th>条目数</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {packs.map((pack) => (
                <tr key={pack.pack_id}>
                  <td>
                    <strong>{pack.name}</strong>
                    <small>{pack.version}</small>
                  </td>
                  <td>{formatJson(pack.scope)}</td>
                  <td>
                    <StatusBadge status={pack.status} />
                  </td>
                  <td>{pack.item_count}</td>
                  <td>
                    {pack.status === "draft" ? (
                      <button
                        className="secondary-button"
                        disabled={isBusy}
                        onClick={() => void handleActivatePack(pack)}
                        type="button"
                      >
                        <Power aria-hidden="true" size={15} />
                        启用
                      </button>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <strong>暂无知识包。</strong>
          <span>批准候选后可由后续流程创建知识包，启用操作会明确展示。</span>
        </div>
      )}
    </section>
  );
}
