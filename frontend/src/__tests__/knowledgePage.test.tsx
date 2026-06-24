import { describe, expect, it, vi } from "vitest";

import { api } from "../api/client";

describe("knowledge API client", () => {
  it("posts candidate decisions and creates knowledge packs", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            candidate_id: "lc_1",
            real_run_id: "run_1",
            task_id: "task_1",
            candidate_type: "alias_candidate",
            status: "approved",
            risk_level: "medium",
            target_field_id: "title",
            proposed_payload: { aliases: ["doc_title"] },
            final_payload: { aliases: ["doc_title"] },
            evidence: {},
            generator: "review_feedback",
            confidence: 0.95,
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            pack_id: "kp_1",
            name: "Title aliases",
            scope: { schema_id: "schema_1" },
            status: "draft",
            version: "1.0.0",
            item_count: 1,
            regression_report_path: null,
            reviewer: "tester",
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      );

    const candidate = await api.decideKnowledgeCandidate("lc_1", {
      decision: "approved",
      reviewer: "tester",
      final_payload: { aliases: ["doc_title"] },
      reason: "reviewed",
    });
    const pack = await api.createKnowledgePack({
      name: "Title aliases",
      scope: { schema_id: "schema_1" },
      candidate_ids: ["lc_1"],
      reviewer: "tester",
    });

    expect(candidate.status).toBe("approved");
    expect(pack.pack_id).toBe("kp_1");
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body)).decision).toBe("approved");
    fetchMock.mockRestore();
  });
});
