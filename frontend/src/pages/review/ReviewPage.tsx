import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { api } from "../../api";
import { KnowledgeGovernancePanel } from "../../components/KnowledgeGovernancePanel";
import { PageState } from "../../components/feedback/PageState";
import type { ReviewImpactPreview, ReviewRecord } from "../../types";

function isLlmSuggestion(review: ReviewRecord) {
  return review.suggested_by?.toLocaleLowerCase().includes("llm") ?? false;
}

export function ReviewPage() {
  const [reviews, setReviews] = useState<ReviewRecord[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [impact, setImpact] = useState<ReviewImpactPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [impactLoading, setImpactLoading] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const queueRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const selectedReview = reviews.find((review) => review.review_id === selectedId) ?? null;

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setImpact(null);
      return;
    }
    let cancelled = false;
    setImpactLoading(true);
    setImpact(null);
    void api.getReviewImpact(selectedId)
      .then((result) => {
        if (!cancelled) setImpact(result);
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "复核影响读取失败。");
        }
      })
      .finally(() => {
        if (!cancelled) setImpactLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const result = await api.listReviews("pending");
      setReviews(result.items);
      setSelectedId((current) =>
        result.items.some((review) => review.review_id === current)
          ? current
          : result.items[0]?.review_id ?? ""
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "待复核队列读取失败。");
    } finally {
      setLoading(false);
    }
  }

  async function decide(decision: "approve" | "reject") {
    if (!selectedReview) return;
    setWorking(true);
    setMessage("");
    try {
      if (decision === "approve") {
        await api.approveReview(selectedReview.review_id);
        setMessage("已采纳该建议。");
      } else {
        await api.rejectReview(selectedReview.review_id);
        setMessage("已拒绝该建议。");
      }
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "复核决策提交失败。");
    } finally {
      setWorking(false);
    }
  }

  function selectByKeyboard(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const nextIndex =
      event.key === "ArrowDown"
        ? Math.min(index + 1, reviews.length - 1)
        : Math.max(index - 1, 0);
    const nextReview = reviews[nextIndex];
    if (!nextReview) return;
    setSelectedId(nextReview.review_id);
    queueRefs.current[nextIndex]?.focus();
  }

  return (
    <section className="route-placeholder operations-page review-page" aria-labelledby="review-title">
      <p className="page-eyebrow">复核</p>
      <h1 id="review-title">复核队列</h1>
      <p className="route-placeholder-description">选择建议后查看其证据与影响，再作出支持的决策。</p>

      {error ? <PageState kind="error" title="复核操作失败" detail={error} /> : null}
      {loading ? <PageState kind="loading" title="正在读取待复核队列" /> : null}
      {!loading && !error && !reviews.length ? <PageState kind="empty" title="当前没有待复核项" /> : null}

      {reviews.length ? (
        <div className="operations-split-pane review-split-pane">
          <section className="review-queue-pane" aria-labelledby="review-queue-title">
            <h2 id="review-queue-title">待复核队列</h2>
            <div role="listbox" aria-label="待复核队列">
              {reviews.map((review, index) => (
                <button
                  key={review.review_id}
                  ref={(element) => { queueRefs.current[index] = element; }}
                  type="button"
                  role="option"
                  aria-selected={review.review_id === selectedId}
                  className="review-queue-item"
                  onClick={() => setSelectedId(review.review_id)}
                  onKeyDown={(event) => selectByKeyboard(event, index)}
                >
                  <strong>{review.source_field_name ?? "未命名来源字段"}</strong>
                  <span>{review.target_field_id ?? "未映射"}</span>
                  {isLlmSuggestion(review) ? <em>LLM 建议</em> : null}
                </button>
              ))}
            </div>
          </section>

          <section className="review-impact-pane" aria-labelledby="review-impact-title">
            <h2 id="review-impact-title">证据与影响</h2>
            {selectedReview ? (
              <>
                <dl>
                  <div><dt>来源字段</dt><dd>{selectedReview.source_field_name ?? "—"}</dd></div>
                  <div><dt>来源路径</dt><dd>{selectedReview.source_path ?? "—"}</dd></div>
                  <div><dt>目标字段</dt><dd>{selectedReview.target_field_id ?? "—"}</dd></div>
                  <div><dt>建议依据</dt><dd>{selectedReview.reason ?? "—"}</dd></div>
                  <div><dt>置信度</dt><dd>{selectedReview.confidence === null ? "—" : `${Math.round(selectedReview.confidence * 100)}%`}</dd></div>
                </dl>
                {impactLoading ? <PageState kind="loading" title="正在读取影响" /> : null}
                {impact ? (
                  <div className="review-impact-result">
                    <p>可能影响的后续映射：{impact.would_affect.length}</p>
                    {impact.risk_flags.length ? <p>风险标记：{impact.risk_flags.join("、")}</p> : null}
                    {impact.badcase_hits.length ? <p>badcase 命中：{impact.badcase_hits.join("、")}</p> : null}
                  </div>
                ) : null}
              </>
            ) : null}
          </section>
        </div>
      ) : null}

      <section className="operations-actions review-actions" aria-label="复核决策">
        <button type="button" className="primary" onClick={() => void decide("approve")} disabled={working || !selectedReview}>
          采纳
        </button>
        <button type="button" onClick={() => void decide("reject")} disabled={working || !selectedReview}>
          拒绝
        </button>
      </section>
      {message ? <p role="status">{message}</p> : null}
      <KnowledgeGovernancePanel />
    </section>
  );
}
