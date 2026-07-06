import { describe, expect, it } from "vitest";

import { canBatchApprove } from "./reviewBatchSafety";

const base = {
  review_id: "r1",
  schema_id: "policy_doc",
  template_id: "policy_doc_base_v1",
  source_field_name: "发文单位",
  target_field_id: "issuer",
  reason: "low confidence"
};

describe("canBatchApprove", () => {
  it("allows identical low-risk mappings", () => {
    expect(canBatchApprove([base, { ...base, review_id: "r2" }])).toBe(true);
  });

  it("blocks mixed mapping scopes", () => {
    expect(
      canBatchApprove([
        base,
        { ...base, review_id: "r2", target_field_id: "publisher" }
      ])
    ).toBe(false);
  });

  it("blocks risk flagged reviews", () => {
    expect(
      canBatchApprove([
        base,
        { ...base, review_id: "r2", reason: "risk_flags=unsafe_alias" }
      ])
    ).toBe(false);
  });
});
