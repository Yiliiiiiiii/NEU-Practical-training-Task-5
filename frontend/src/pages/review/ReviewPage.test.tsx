// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../api";
import { ReviewPage } from "./ReviewPage";

vi.mock("../../api", () => ({
  api: {
    listReviews: vi.fn(),
    getReviewImpact: vi.fn(),
    approveReview: vi.fn(),
    rejectReview: vi.fn(),
    listKnowledgeCandidates: vi.fn(),
    listKnowledgePacks: vi.fn(),
    getKnowledgeMetrics: vi.fn(),
    getKnowledgeLoopReport: vi.fn(),
    acceptKnowledgeCandidate: vi.fn(),
    createKnowledgePack: vi.fn(),
    activateKnowledgePack: vi.fn()
  }
}));

describe("ReviewPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listReviews).mockResolvedValue({
      total: 2,
      items: [
        {
          review_id: "review-1",
          task_id: "task-1",
          doc_id: "doc-1",
          schema_id: "meeting",
          template_id: "meeting-v1",
          source_field_name: "会议主题",
          source_path: "sections[0].title",
          target_field_id: "subject",
          suggested_by: "LLM",
          confidence: 0.84,
          reason: "名称相似",
          status: "pending",
          reviewer: "",
          review_comment: null,
          created_at: "2026-07-01T00:00:00Z",
          updated_at: "2026-07-01T00:00:00Z"
        },
        {
          review_id: "review-2",
          task_id: "task-2",
          doc_id: "doc-2",
          schema_id: "invoice",
          template_id: "invoice-v1",
          source_field_name: "发票号",
          source_path: "fields.invoiceNumber",
          target_field_id: "invoice_number",
          suggested_by: "rule",
          confidence: 0.91,
          reason: "别名规则",
          status: "pending",
          reviewer: "",
          review_comment: null,
          created_at: "2026-07-02T00:00:00Z",
          updated_at: "2026-07-02T00:00:00Z"
        }
      ]
    });
    vi.mocked(api.getReviewImpact).mockResolvedValue({
      review_id: "review-1",
      would_affect: [],
      risk_flags: [],
      badcase_hits: []
    });
    vi.mocked(api.approveReview).mockResolvedValue(undefined);
    vi.mocked(api.rejectReview).mockResolvedValue(undefined);
    vi.mocked(api.listKnowledgeCandidates).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(api.listKnowledgePacks).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(api.getKnowledgeMetrics).mockResolvedValue({
      pending_reviews: 0,
      approved_reviews: 0,
      rejected_reviews: 0,
      pending_candidates: 0,
      accepted_candidates: 0,
      rejected_candidates: 0,
      blocked_candidates: 0,
      draft_packs: 0,
      active_packs: 0,
      archived_packs: 0
    });
    vi.mocked(api.getKnowledgeLoopReport).mockResolvedValue({
      status: "unavailable",
      recommended_command: "python scripts/eval_real_world_knowledge_loop.py"
    });
  });

  afterEach(cleanup);

  it("keeps supported review decisions active", async () => {
    render(<ReviewPage />);

    expect(await screen.findByRole("option", { name: /会议主题/ })).toBeInTheDocument();
    expect(screen.getByText("LLM 建议")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "采纳" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "拒绝" })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "采纳" }));
    await waitFor(() =>
      expect(api.approveReview).toHaveBeenCalledWith("review-1")
    );
  });

  it("exposes supported knowledge candidate and pack governance actions", async () => {
    vi.mocked(api.listKnowledgeCandidates).mockResolvedValue({
      total: 2,
      items: [
        {
          candidate_id: "candidate-pending",
          review_id: "review-1",
          schema_id: "notice",
          template_id: "notice-v1",
          target_field_id: "title",
          alias: "待接受别名",
          candidate_type: "alias",
          support_count: 1,
          badcase_hit: false,
          status: "pending",
          created_at: "2026-07-12T00:00:00Z",
          updated_at: "2026-07-12T00:00:00Z"
        },
        {
          candidate_id: "candidate-accepted",
          review_id: "review-2",
          schema_id: "notice",
          template_id: "notice-v1",
          target_field_id: "title",
          alias: "已接受别名",
          candidate_type: "alias",
          support_count: 1,
          badcase_hit: false,
          status: "accepted",
          created_at: "2026-07-12T00:00:00Z",
          updated_at: "2026-07-12T00:00:00Z"
        }
      ]
    });
    vi.mocked(api.listKnowledgePacks).mockResolvedValue({
      total: 1,
      items: [{
        pack_id: "pack-draft",
        name: "Notice 知识包",
        schema_id: "notice",
        template_id: "notice-v1",
        version: "1",
        status: "draft",
        created_by: "demo_user",
        metadata: {},
        items: [],
        created_at: "2026-07-12T00:00:00Z",
        activated_at: null,
        updated_at: "2026-07-12T00:00:00Z"
      }]
    });
    vi.mocked(api.acceptKnowledgeCandidate).mockResolvedValue(undefined);
    vi.mocked(api.createKnowledgePack).mockResolvedValue(undefined);
    vi.mocked(api.activateKnowledgePack).mockResolvedValue(undefined);

    render(<ReviewPage />);

    expect(await screen.findByText("待接受别名")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "接受候选" }));
    await waitFor(() => expect(api.acceptKnowledgeCandidate).toHaveBeenCalledWith("candidate-pending"));

    fireEvent.click(screen.getByRole("button", { name: "创建知识包草案" }));
    await waitFor(() => expect(api.createKnowledgePack).toHaveBeenCalledWith("notice", "notice-v1"));

    fireEvent.click(screen.getByRole("button", { name: "激活知识包" }));
    await waitFor(() => expect(api.activateKnowledgePack).toHaveBeenCalledWith("pack-draft"));
    expect(api.getKnowledgeLoopReport).toHaveBeenCalled();
  });
});
