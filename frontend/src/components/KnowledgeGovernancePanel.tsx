import { useEffect, useState } from "react";

import { api } from "../api";
import type {
  KnowledgeCandidate,
  KnowledgeLoopApiResponse,
  KnowledgeMetrics,
  KnowledgePack
} from "../types";
import { PageState } from "./feedback/PageState";
import { DataTable } from "./tables/DataTable";

export function KnowledgeGovernancePanel() {
  const [candidates, setCandidates] = useState<KnowledgeCandidate[]>([]);
  const [packs, setPacks] = useState<KnowledgePack[]>([]);
  const [metrics, setMetrics] = useState<KnowledgeMetrics | null>(null);
  const [knowledgeLoop, setKnowledgeLoop] = useState<KnowledgeLoopApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [candidateResult, packResult, metricResult, knowledgeLoopResult] = await Promise.all([
        api.listKnowledgeCandidates(),
        api.listKnowledgePacks(),
        api.getKnowledgeMetrics(),
        api.getKnowledgeLoopReport()
      ]);
      setCandidates(candidateResult.items);
      setPacks(packResult.items);
      setMetrics(metricResult);
      setKnowledgeLoop(knowledgeLoopResult);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "知识治理数据读取失败。");
    } finally {
      setLoading(false);
    }
  }

  async function acceptCandidate(candidateId: string) {
    setWorking(true);
    setMessage("");
    try {
      await api.acceptKnowledgeCandidate(candidateId);
      setMessage("已接受知识候选。");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "接受知识候选失败。");
    } finally {
      setWorking(false);
    }
  }

  async function createPack(candidate: KnowledgeCandidate) {
    setWorking(true);
    setMessage("");
    try {
      await api.createKnowledgePack(candidate.schema_id, candidate.template_id);
      setMessage("已创建知识包草案。");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建知识包失败。");
    } finally {
      setWorking(false);
    }
  }

  async function activatePack(packId: string) {
    setWorking(true);
    setMessage("");
    try {
      await api.activateKnowledgePack(packId);
      setMessage("已激活知识包。");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "激活知识包失败。");
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="operations-section" aria-labelledby="knowledge-governance-title">
      <h2 id="knowledge-governance-title">知识治理</h2>
      {loading ? <PageState kind="loading" title="正在读取知识治理数据" /> : null}
      {error ? <PageState kind="error" title="知识治理读取失败" detail={error} /> : null}
      {!loading && !error ? (
        <>
          <section aria-labelledby="knowledge-metrics-title">
            <h3 id="knowledge-metrics-title">知识治理指标</h3>
            <dl>
              <div><dt>待接受候选</dt><dd>{metrics?.pending_candidates ?? 0}</dd></div>
              <div><dt>已接受候选</dt><dd>{metrics?.accepted_candidates ?? 0}</dd></div>
              <div><dt>草案知识包</dt><dd>{metrics?.draft_packs ?? 0}</dd></div>
              <div><dt>已激活知识包</dt><dd>{metrics?.active_packs ?? 0}</dd></div>
            </dl>
          </section>

          <section aria-labelledby="knowledge-candidates-title">
            <h3 id="knowledge-candidates-title">知识候选</h3>
            {!candidates.length ? <PageState kind="empty" title="暂无知识候选" /> : (
              <DataTable label="知识候选列表">
                <table>
                  <thead><tr><th>候选</th><th>目标字段</th><th>Schema / 模板</th><th>状态</th><th>操作</th></tr></thead>
                  <tbody>
                    {candidates.map((candidate) => (
                      <tr key={candidate.candidate_id}>
                        <td>{candidate.alias}</td>
                        <td>{candidate.target_field_id}</td>
                        <td>{candidate.schema_id} / {candidate.template_id}</td>
                        <td>{candidate.status}</td>
                        <td>
                          {candidate.status === "pending" ? (
                            <button type="button" disabled={working} onClick={() => void acceptCandidate(candidate.candidate_id)}>接受候选</button>
                          ) : null}
                          {candidate.status === "accepted" ? (
                            <button type="button" disabled={working} onClick={() => void createPack(candidate)}>创建知识包草案</button>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </DataTable>
            )}
          </section>

          <section aria-labelledby="knowledge-packs-title">
            <h3 id="knowledge-packs-title">知识包</h3>
            {!packs.length ? <PageState kind="empty" title="暂无知识包" /> : (
              <DataTable label="知识包列表">
                <table>
                  <thead><tr><th>名称</th><th>Schema / 模板</th><th>版本</th><th>状态</th><th>操作</th></tr></thead>
                  <tbody>
                    {packs.map((pack) => (
                      <tr key={pack.pack_id}>
                        <td>{pack.name}</td>
                        <td>{pack.schema_id} / {pack.template_id}</td>
                        <td>{pack.version}</td>
                        <td>{pack.status}</td>
                        <td>{pack.status === "draft" ? <button type="button" disabled={working} onClick={() => void activatePack(pack.pack_id)}>激活知识包</button> : null}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </DataTable>
            )}
          </section>

          <section aria-labelledby="knowledge-loop-title">
            <h3 id="knowledge-loop-title">知识闭环评估</h3>
            {!knowledgeLoop ? <PageState kind="empty" title="暂无知识闭环评估结果" /> : null}
            {knowledgeLoop?.status === "unavailable" ? <PageState kind="empty" title="知识闭环评估不可用" detail={knowledgeLoop.recommended_command} /> : null}
            {knowledgeLoop?.status === "available" ? (
              <dl>
                <div><dt>已接受候选</dt><dd>{knowledgeLoop.report.approved_candidates}</dd></div>
                <div><dt>已拒绝候选</dt><dd>{knowledgeLoop.report.rejected_candidates}</dd></div>
                <div><dt>badcase 违规</dt><dd>{knowledgeLoop.report.badcase_violation_count}</dd></div>
              </dl>
            ) : null}
          </section>
        </>
      ) : null}
      {message ? <p role="status">{message}</p> : null}
    </section>
  );
}
