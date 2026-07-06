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
      setMessage(caught instanceof Error ? caught.message : "Review Workbench failed.");
    } finally {
      setWorking(false);
    }
  }

  async function preview(reviewId: string) {
    setWorking(true);
    try {
      setImpact(await api.getReviewImpact(reviewId));
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Impact preview failed.");
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
      setMessage(`${selectedIds.length} reviews approved.`);
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
      setMessage(`${selectedIds.length} reviews rejected with negative knowledge.`);
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
          <span>pending</span>
          <strong>{summary?.pending ?? 0}</strong>
          <span>resolution</span>
          <strong>{Math.round((summary?.resolution_rate ?? 0) * 100)}%</strong>
          <span>negative rules</span>
          <strong>{summary?.negative_rule_count ?? 0}</strong>
          <span>conflicts</span>
          <strong>{conflicts?.total ?? 0}</strong>
        </div>
        <button type="button" className="icon-button" onClick={() => void load()} title="Refresh">
          <RefreshCw size={16} />
        </button>
      </div>

      <div className="review-filter-row">
        <Users size={16} />
        <label>
          <span>Group by</span>
          <select value={groupBy} onChange={(event) => setGroupBy(event.target.value)}>
            <option value="schema_id">Schema</option>
            <option value="target_field">Target field</option>
            <option value="source_label">Source label</option>
            <option value="confidence_tier">Confidence</option>
            <option value="risk_flag">Risk flag</option>
          </select>
        </label>
        <small>{grouped?.items.length ?? 0} groups</small>
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
                <strong>{review.source_field_name ?? "unknown"}</strong>
                <small>{review.target_field_id ?? "unmapped"}</small>
              </span>
              <em>{Math.round((review.confidence ?? 0) * 100)}%</em>
              <button
                type="button"
                className="icon-button"
                title="Impact preview"
                onClick={(event) => {
                  event.preventDefault();
                  void preview(review.review_id);
                }}
              >
                <Eye size={15} />
              </button>
            </label>
          ))}
          {!reviews.length ? <p className="quiet">No pending reviews.</p> : null}
        </div>

        <div className="review-evidence-pane">
          {selectedReview ? (
            <>
              <span>Evidence</span>
              <strong>{selectedReview.source_field_name ?? "unknown"}</strong>
              <p>{selectedReview.source_path ?? "No source path"}</p>
              <p>{selectedReview.reason ?? "No review reason"}</p>
            </>
          ) : (
            <p className="quiet">Select a review to inspect evidence.</p>
          )}
          {impact ? (
            <div className="review-impact">
              <span>Impact preview</span>
              <strong>{impact.would_affect.length} future mappings</strong>
              {impact.risk_flags.length ? (
                <small>{impact.risk_flags.join(", ")}</small>
              ) : null}
              {impact.badcase_hits.length ? (
                <small className="risk-text">
                  <ShieldAlert size={13} /> badcase hit
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
          Approve Batch
        </button>
        <button
          type="button"
          disabled={working || !selectedIds.length}
          onClick={() => void batchReject()}
        >
          <XCircle size={15} />
          Reject Batch
        </button>
      </div>
      {message ? <p className="quiet">{message}</p> : null}
    </div>
  );
}
