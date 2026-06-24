import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL, api } from "../api/client";
import { KnowledgePage } from "../pages/KnowledgePage";

const jsonHeaders = { "content-type": "application/json" };

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), { status: 200, headers: jsonHeaders });
}

function fetchCall(index: number) {
  const fetchMock = vi.mocked(globalThis.fetch);
  const [url, init] = fetchMock.mock.calls[index];

  return {
    body: init?.body ? JSON.parse(String(init.body)) : undefined,
    init,
    path: String(url).replace(API_BASE_URL, ""),
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("knowledge API client", () => {
  it("calls all knowledge endpoints with expected urls, methods, and bodies", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({
          real_run_id: "run_1",
          task_id: "task_1",
          doc_id: "doc_1",
          schema_id: "schema_1",
          template_id: "template_1",
          input_hash: "sha256:abc",
          status: "captured",
          summary: { mapped_fields: 1 },
          report_paths: { mapping_report: "tasks/task_1/mapping_report.json" },
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              candidate_id: "lc_1",
              real_run_id: "run_1",
              task_id: "task_1",
              candidate_type: "alias_candidate",
              status: "pending",
              risk_level: "medium",
              target_field_id: "title",
              proposed_payload: { aliases: ["doc_title"] },
              final_payload: {},
              evidence: {},
              generator: "review_feedback",
              confidence: 0.95,
            },
          ],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              candidate_id: "lc_1",
              real_run_id: "run_1",
              task_id: "task_1",
              candidate_type: "alias_candidate",
              status: "pending",
              risk_level: "medium",
              target_field_id: "title",
              proposed_payload: { aliases: ["doc_title"] },
              final_payload: {},
              evidence: {},
              generator: "review_feedback",
              confidence: 0.95,
            },
          ],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
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
      )
      .mockResolvedValueOnce(
        jsonResponse({
          pack_id: "kp_1",
          name: "Title aliases",
          scope: { schema_id: "schema_1" },
          status: "draft",
          version: "1.0.0",
          item_count: 1,
          regression_report_path: null,
          reviewer: "tester",
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              pack_id: "kp_1",
              name: "Title aliases",
              scope: { schema_id: "schema_1" },
              status: "draft",
              version: "1.0.0",
              item_count: 1,
              regression_report_path: null,
              reviewer: "tester",
            },
          ],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          pack_id: "kp_1",
          name: "Title aliases",
          scope: { schema_id: "schema_1" },
          status: "active",
          version: "1.0.0",
          item_count: 1,
          regression_report_path: null,
          reviewer: "tester",
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          real_runs: 1,
          pending_candidates: 0,
          approved_candidates: 1,
          rejected_candidates: 0,
          active_packs: 1,
        }),
      );

    const run = await api.captureKnowledgeRun("task_1");
    const derived = await api.deriveKnowledgeCandidates("run_1");
    const candidates = await api.listKnowledgeCandidates("approved");
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
    const packs = await api.listKnowledgePacks();
    const activated = await api.activateKnowledgePack("kp_1");
    const metrics = await api.getKnowledgeMetrics();

    expect(run.doc_id).toBe("doc_1");
    expect(derived.items[0].candidate_id).toBe("lc_1");
    expect(candidates.items[0].status).toBe("pending");
    expect(candidate.status).toBe("approved");
    expect(pack.pack_id).toBe("kp_1");
    expect(packs.items[0].pack_id).toBe("kp_1");
    expect(activated.status).toBe("active");
    expect(metrics.active_packs).toBe(1);

    expect(fetchCall(0)).toMatchObject({
      body: {},
      init: { method: "POST" },
      path: "/knowledge/real-runs/from-task/task_1",
    });
    expect(fetchCall(1)).toMatchObject({
      body: {},
      init: { method: "POST" },
      path: "/knowledge/real-runs/run_1/derive",
    });
    expect(fetchCall(2)).toMatchObject({
      body: undefined,
      path: "/knowledge/candidates?status=approved",
    });
    expect(fetchCall(2).init?.method).toBeUndefined();
    expect(fetchCall(3)).toMatchObject({
      body: {
        decision: "approved",
        final_payload: { aliases: ["doc_title"] },
        reason: "reviewed",
        reviewer: "tester",
      },
      init: { method: "POST" },
      path: "/knowledge/candidates/lc_1/decision",
    });
    expect(fetchCall(4)).toMatchObject({
      body: {
        candidate_ids: ["lc_1"],
        name: "Title aliases",
        reviewer: "tester",
        scope: { schema_id: "schema_1" },
      },
      init: { method: "POST" },
      path: "/knowledge/packs",
    });
    expect(fetchCall(5)).toMatchObject({
      body: undefined,
      path: "/knowledge/packs",
    });
    expect(fetchCall(5).init?.method).toBeUndefined();
    expect(fetchCall(6)).toMatchObject({
      body: {},
      init: { method: "POST" },
      path: "/knowledge/packs/kp_1/activate",
    });
    expect(fetchCall(7)).toMatchObject({
      body: undefined,
      path: "/knowledge/metrics",
    });
    expect(fetchCall(7).init?.method).toBeUndefined();
  });
});

describe("KnowledgePage", () => {
  it("loads pending candidates and approves one", async () => {
    vi.spyOn(api, "getKnowledgeMetrics").mockResolvedValue({
      real_runs: 1,
      pending_candidates: 1,
      approved_candidates: 0,
      rejected_candidates: 0,
      active_packs: 0,
    });
    vi.spyOn(api, "listKnowledgeCandidates").mockResolvedValue({
      items: [
        {
          candidate_id: "lc_1",
          real_run_id: "run_1",
          task_id: "task_1",
          candidate_type: "alias_candidate",
          status: "pending",
          risk_level: "medium",
          target_field_id: "title",
          proposed_payload: { aliases: ["doc_title"] },
          final_payload: {},
          evidence: { source_name: "doc_title" },
          generator: "review_feedback",
          confidence: 0.95,
        },
      ],
    });
    vi.spyOn(api, "listKnowledgePacks").mockResolvedValue({ items: [] });
    vi.spyOn(api, "decideKnowledgeCandidate").mockResolvedValue({
      candidate_id: "lc_1",
      real_run_id: "run_1",
      task_id: "task_1",
      candidate_type: "alias_candidate",
      status: "approved",
      risk_level: "medium",
      target_field_id: "title",
      proposed_payload: { aliases: ["doc_title"] },
      final_payload: { aliases: ["doc_title"] },
      evidence: { source_name: "doc_title" },
      generator: "review_feedback",
      confidence: 0.95,
    });
    const captureRun = vi.spyOn(api, "captureKnowledgeRun").mockResolvedValue({
      real_run_id: "run_1",
      task_id: "task_1",
      doc_id: "doc_1",
      schema_id: "schema_1",
      template_id: "template_1",
      input_hash: "sha256:abc",
      status: "captured",
      summary: {},
      report_paths: {},
    });
    const deriveCandidates = vi.spyOn(api, "deriveKnowledgeCandidates").mockResolvedValue({
      items: [],
    });
    const activatePack = vi.spyOn(api, "activateKnowledgePack").mockResolvedValue({
      pack_id: "kp_1",
      name: "Title aliases",
      scope: { schema_id: "schema_1" },
      status: "active",
      version: "1.0.0",
      item_count: 1,
      regression_report_path: null,
      reviewer: "tester",
    });

    render(
      <KnowledgePage
        onToast={vi.fn()}
        selection={{ docId: null, schemaId: null, templateId: null, taskId: null, taskStatus: null }}
      />,
    );

    expect(await screen.findByText("alias_candidate")).toBeInTheDocument();
    expect(captureRun).not.toHaveBeenCalled();
    expect(deriveCandidates).not.toHaveBeenCalled();
    expect(activatePack).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /批准/i }));

    await waitFor(() => expect(api.decideKnowledgeCandidate).toHaveBeenCalled());
  });
});
