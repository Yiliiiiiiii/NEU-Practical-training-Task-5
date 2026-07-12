import { Eye, RefreshCw, ShieldAlert, Users, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api";
import { canBatchApprove } from "../reviewBatchSafety";
import type {
  KnowledgeConflictResponse,
  ReviewGroupedResponse,
  ReviewImpactPreview,
  ReviewRecord,
  ReviewWorkbenchSummary
} from "../types";

export function ReviewWorkbenchPanel() {
  const [summary, setSummary] = useState<ReviewWorkbenchSummary | null>(null);
  const [reviews, setReviews] = useState<ReviewRecord[]>([]);
  const [grouped, setGrouped] = useState<ReviewGroupedResponse | null>(null);
  const [conflicts, setConflicts] = useState<KnowledgeConflictResponse | null>(null);
  const [impact, setImpact] = useState<ReviewImpactPreview | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [groupBy, setGroupBy] = useState("schema_id");
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState("");

  const selectedReviews = useMemo(
    () => reviews.filter((review) => selectedIds.includes(review.review_id)),
    [reviews, selectedIds]
  );
  const selectedReview =
    reviews.find((review) => review.review_id === selectedIds[selectedIds.length - 1]) ??
    null;

  useEffect(() => {
    void load();
  }, [groupBy]);

  async function load() {
    setWorking(true);
    try {
      const [summaryResult, reviewResult, groupedResult, conflictResult] =
        await Promise.all([
          api.getReviewSummary(),
          api.listReviews("pending"),
          api.getGroupedReviews(groupBy),
          api.getKnowledgeConflicts()
        ]);
      setSummary(summaryResult);
      setReviews(reviewResult.items);
      setGrouped(groupedResult);
      setConflicts(conflictResult);
      setSelectedIds((current) =>
        current.filter((id) => reviewResult.items.some((item) => item.review_id === id))
      );
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "复核工作台读取失败。");
    } finally {
      setWorking(false);
    }
  }

  async function preview(reviewId: string) {
    setWorking(true);
    try {
      setImpact(await api.getReviewImpact(reviewId));
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "影响预览读取失败。");
    } finally {
      setWorking(false);
    }
  }

  async function batchApprove() {
    if (!canBatchApprove(selectedReviews)) {
      return;
    }
    setWorking(true);
    try {
      await api.batchApproveReviews(selectedIds);
      setMessage(`已采纳 ${selectedIds.length} 个复核建议。`);
      setSelectedIds([]);
      await load();
    } finally {
      setWorking(false);
    }
  }

  async function batchReject() {
    if (!selectedIds.length) {
      return;
    }
    setWorking(true);
    try {
      await api.batchRejectReviews(selectedIds);
      setMessage(`已拒绝 ${selectedIds.length} 个复核建议，并保留负向知识。`);
      setSelectedIds([]);
      await load();
    } finally {
      setWorking(false);
    }
  }

  function toggle(reviewId: string) {
    setSelectedIds((current) =>
      current.includes(reviewId)
        ? current.filter((item) => item !== reviewId)
        : [...current, reviewId]
    );
  }

  return (
    <div className="governance-panel review-workbench">
      <div className="governance-toolbar">
        <div className="governance-summary">
          <span>待复核</span>
          <strong>{summary?.pending ?? 0}</strong>
          <span>解决率</span>
          <strong>{Math.round((summary?.resolution_rate ?? 0) * 100)}%</strong>
          <span>负向规则</span>
          <strong>{summary?.negative_rule_count ?? 0}</strong>
          <span>冲突</span>
          <strong>{conflicts?.total ?? 0}</strong>
        </div>
        <button type="button" className="icon-button" onClick={() => void load()} title="刷新">
          <RefreshCw size={16} />
        </button>
      </div>

      <div className="review-filter-row">
        <Users size={16} />
        <label>
          <span>分组方式</span>
          <select value={groupBy} onChange={(event) => setGroupBy(event.target.value)}>
            <option value="schema_id">Schema</option>
            <option value="target_field">目标字段</option>
            <option value="source_label">来源标签</option>
            <option value="confidence_tier">置信度</option>
            <option value="risk_flag">风险标记</option>
          </select>
        </label>
        <small>{grouped?.items.length ?? 0} 个分组</small>
      </div>

      <div className="review-workbench-grid">
        <div className="review-workbench-list">
          {reviews.slice(0, 12).map((review) => (
            <label key={review.review_id} className="review-workbench-row">
              <input
                type="checkbox"
                checked={selectedIds.includes(review.review_id)}
                onChange={() => toggle(review.review_id)}
              />
              <span>
                <strong>{review.source_field_name ?? "未知来源字段"}</strong>
                <small>{review.target_field_id ?? "未映射"}</small>
              </span>
              <em>{Math.round((review.confidence ?? 0) * 100)}%</em>
              <button
                type="button"
                className="icon-button"
                title="影响预览"
                onClick={(event) => {
                  event.preventDefault();
                  void preview(review.review_id);
                }}
              >
                <Eye size={15} />
              </button>
            </label>
          ))}
          {!reviews.length ? <p className="quiet">当前没有待复核项。</p> : null}
        </div>

        <div className="review-evidence-pane">
          {selectedReview ? (
            <>
              <span>证据</span>
              <strong>{selectedReview.source_field_name ?? "未知来源字段"}</strong>
              <p>{selectedReview.source_path ?? "无来源路径"}</p>
              <p>{selectedReview.reason ?? "无复核依据"}</p>
            </>
          ) : (
            <p className="quiet">选择一项复核以查看证据。</p>
          )}
          {impact ? (
            <div className="review-impact">
              <span>影响预览</span>
              <strong>{impact.would_affect.length} 个后续映射</strong>
              {impact.risk_flags.length ? (
                <small>{impact.risk_flags.join(", ")}</small>
              ) : null}
              {impact.badcase_hits.length ? (
                <small className="risk-text">
                  <ShieldAlert size={13} /> badcase 命中
                </small>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      <div className="review-batch-actions">
        <button
          type="button"
          className="primary"
          disabled={working || !canBatchApprove(selectedReviews)}
          onClick={() => void batchApprove()}
        >
          批量采纳
        </button>
        <button
          type="button"
          disabled={working || !selectedIds.length}
          onClick={() => void batchReject()}
        >
          <XCircle size={15} />
          批量拒绝
        </button>
      </div>
      {message ? <p className="quiet">{message}</p> : null}
    </div>
  );
}
