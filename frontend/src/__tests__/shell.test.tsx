import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "../App";

describe("workbench shell", () => {
  it("shows document workbench navigation", () => {
    render(<App />);

    expect(screen.getByRole("button", { name: /Import/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Tasks/i })).toBeInTheDocument();
    expect(screen.getByText(/UIR -> Schema -> Mapping -> Transform/i)).toBeInTheDocument();
    expect(screen.getByText(/Canonical -> Render -> Validate -> Manifest -> Zip/i)).toBeInTheDocument();
  });

  it("shows the eight-step SchemaFlow pipeline", () => {
    render(<App />);

    const pipeline = screen.getByLabelText("SchemaFlow pipeline");
    expect(within(pipeline).getAllByRole("listitem")).toHaveLength(8);
    expect(within(pipeline).getByText("Human review")).toBeInTheDocument();
    expect(within(pipeline).getByText("Validate")).toBeInTheDocument();
  });
});
