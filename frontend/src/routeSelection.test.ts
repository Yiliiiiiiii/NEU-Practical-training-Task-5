import { describe, expect, it } from "vitest";

import { resolveRouteSelection } from "./routeSelection";

const route = {
  selected_schema_id: null,
  selected_template_id: null,
  confidence: 0.42,
  review_required: true,
  candidates: [
    {
      schema_id: "meeting_doc",
      template_id: "meeting_doc_base_v1",
      confidence: 0.42
    },
    {
      schema_id: "general_doc",
      template_id: "general_doc_base_v1",
      confidence: 0.2
    }
  ]
};

describe("resolveRouteSelection", () => {
  it("blocks review-required routes until a candidate is chosen and confirmed", () => {
    expect(resolveRouteSelection(route, "", false)).toEqual({
      schemaId: "",
      templateId: "",
      canCreate: false,
      requiresConfirmation: true
    });
  });

  it("resolves a manual override from existing candidates", () => {
    expect(resolveRouteSelection(route, "general_doc", true)).toEqual({
      schemaId: "general_doc",
      templateId: "general_doc_base_v1",
      canCreate: true,
      requiresConfirmation: false
    });
  });

  it("uses a confident selected route without extra confirmation", () => {
    const confident = {
      ...route,
      selected_schema_id: "meeting_doc",
      selected_template_id: "meeting_doc_base_v1",
      confidence: 0.82,
      review_required: false
    };

    expect(resolveRouteSelection(confident, "", false).canCreate).toBe(true);
  });
});
