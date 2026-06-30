import { describe, expect, it } from "vitest";

import { filterChunks, suggestedAction, truncateSha } from "./evidence";

describe("evidence helpers", () => {
  it("keeps table chunks with quality findings", () => {
    const chunks = [
      { chunk_id: "a", content_tags: ["table"], quality_flags: ["oversized"] },
      { chunk_id: "b", content_tags: ["paragraph"], quality_flags: [] }
    ];

    expect(filterChunks(chunks, { strategy: "all", tablesOnly: true, flaggedOnly: true }))
      .toEqual([chunks[0]]);
  });

  it("uses deterministic validation advice", () => {
    expect(suggestedAction({ severity: "error", message: "missing" }))
      .toBe("Review the source evidence and complete or reject this field.");
  });

  it("preserves the full checksum outside compact display", () => {
    expect(truncateSha("a".repeat(64))).toBe("aaaaaaaaaaaa…aaaaaaa");
  });
});
