import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ImportPage } from "../pages/ImportPage";

describe("ImportPage", () => {
  it("offers demo UIR, schema, and template import panels", () => {
    render(<ImportPage />);

    expect(screen.getByText("UIR Document")).toBeInTheDocument();
    expect(screen.getByText("Target Schema")).toBeInTheDocument();
    expect(screen.getByText("Mapping Template")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /加载 general demo/i })).toBeInTheDocument();
  });
});
