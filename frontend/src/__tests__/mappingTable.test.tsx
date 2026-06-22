import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MappingTable } from "../components/MappingTable";

describe("MappingTable", () => {
  it("marks review-required mappings", () => {
    render(
      <MappingTable
        mappings={[
          {
            mapping_id: "m1",
            task_id: "t1",
            candidate_id: "c1",
            source_name: "Title",
            source_path: "metadata.title",
            target_field_id: "title",
            target_field_name: "title",
            method: "alias_match",
            confidence: 0.72,
            status: "pending_review",
            need_review: true,
            evidence: ["alias"],
          },
        ]}
        onReview={() => undefined}
        targetFields={["title"]}
      />,
    );

    expect(screen.getByText("Needs review")).toBeInTheDocument();
  });
});
