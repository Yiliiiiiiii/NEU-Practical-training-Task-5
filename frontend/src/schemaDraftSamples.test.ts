import { describe, expect, it } from "vitest";

import { parseSchemaDraftSamples } from "./schemaDraftSamples";

describe("parseSchemaDraftSamples", () => {
  it("accepts a non-empty array of UIR documents", () => {
    const documents = parseSchemaDraftSamples(
      JSON.stringify([{ uir_version: "1.0", doc_id: "sample_1", blocks: [] }])
    );

    expect(documents).toHaveLength(1);
    expect(documents[0].doc_id).toBe("sample_1");
  });

  it("rejects an object payload", () => {
    expect(() => parseSchemaDraftSamples('{"doc_id":"sample_1"}')).toThrow(
      "Sample JSON must be a non-empty array."
    );
  });

  it("rejects empty sample arrays", () => {
    expect(() => parseSchemaDraftSamples("[]")).toThrow(
      "Sample JSON must be a non-empty array."
    );
  });
});
