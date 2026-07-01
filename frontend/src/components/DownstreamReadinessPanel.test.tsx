// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DownstreamReadinessPanel } from "./DownstreamReadinessPanel";

describe("DownstreamReadinessPanel", () => {
  it("shows CSV, RAG, and contract readiness from live artifacts", () => {
    render(
      <DownstreamReadinessPanel
        manifest={{
          manifest_version: "1.1",
          package_id: "pkg",
          package_version: "1.0.0",
          task_id: "task",
          doc_id: "doc",
          created_at: "2026-07-01",
          generator: {},
          files: [
            { path: "content.json", size_bytes: 1, sha256: "a" },
            { path: "chunks.jsonl", size_bytes: 1, sha256: "b" }
          ]
        }}
        chunks={{
          total: 1,
          items: [{ chunk_id: "c1", text: "正文", source_block_ids: ["b1"] }]
        }}
        verifier={{ passed: true, errors: [], warnings: [] }}
      />
    );

    expect(screen.getByText("CSV ready")).toBeTruthy();
    expect(screen.getByText("RAG ready")).toBeTruthy();
    expect(screen.getByText("Contract passed")).toBeTruthy();
  });
});
