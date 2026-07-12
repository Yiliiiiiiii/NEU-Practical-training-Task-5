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
    rejectReview: vi.fn()
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
  });

  afterEach(cleanup);

  it("keeps supported decisions active and explains that defer is unavailable", async () => {
    render(<ReviewPage />);

    expect(await screen.findByRole("option", { name: /会议主题/ })).toBeInTheDocument();
    expect(screen.getByText("LLM 建议")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "采纳" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "拒绝" })).toBeEnabled();
    expect(
      screen.getByRole("button", { name: "暂缓（当前 API 不支持）" })
    ).toBeDisabled();
    expect(screen.getByText("暂缓操作原因：当前 API 不支持。"))
      .toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "采纳" }));
    await waitFor(() =>
      expect(api.approveReview).toHaveBeenCalledWith("review-1")
    );
  });
});
