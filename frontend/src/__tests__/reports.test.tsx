import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ReportTabs } from "../components/ReportTabs";

describe("ReportTabs", () => {
  it("renders mapping, validation, consistency, and trace tabs", () => {
    render(
      <ReportTabs
        reports={{ mapping: {}, validation: {}, consistency: {}, trace: {} }}
      />,
    );

    expect(screen.getByRole("button", { name: /Mapping/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Validation/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Consistency/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Trace/i })).toBeInTheDocument();
  });
});
