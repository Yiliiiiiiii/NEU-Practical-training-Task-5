import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "../App";

describe("workbench shell", () => {
  it("shows document workbench navigation", () => {
    render(<App />);

    expect(screen.getByRole("button", { name: /Import/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Tasks/i })).toBeInTheDocument();
    expect(screen.getByText(/UIR -> Schema -> Template/i)).toBeInTheDocument();
  });
});
