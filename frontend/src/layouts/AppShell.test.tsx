// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { useRoute } from "../app/router";
import { AppShell } from "./AppShell";

vi.mock("../api", () => ({
  api: {
    listSchemas: vi.fn()
  }
}));

function RouteHarness() {
  const route = useRoute();

  return (
    <AppShell route={route}>
      <h1>Content</h1>
    </AppShell>
  );
}

afterEach(cleanup);

describe("AppShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listSchemas).mockResolvedValue({ items: [], total: 0 });
  });

  it("renders the global navigation and updates the active route", () => {
    window.history.replaceState({}, "", "/review");
    render(<RouteHarness />);

    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(8);
    expect(links.map((link) => link.getAttribute("href"))).toEqual(
      expect.arrayContaining(["/", "/conversions/new", "/tasks", "/review", "/schemapacks"])
    );
    expect(links.find((link) => link.getAttribute("href") === "/review")).toHaveAttribute(
      "aria-current",
      "page"
    );
  });

  it("updates navigation after history changes and can collapse the sidebar", () => {
    window.history.replaceState({}, "", "/");
    render(<RouteHarness />);

    const navigationButton = screen.getAllByRole("button")[0];
    fireEvent.click(navigationButton);
    expect(document.querySelector(".application-shell")).toHaveClass("is-navigation-collapsed");

    const tasksLink = screen.getAllByRole("link").find((link) => link.getAttribute("href") === "/tasks");
    fireEvent.click(tasksLink!);
    expect(tasksLink).toHaveAttribute("aria-current", "page");

    window.history.pushState({}, "", "/settings");
    fireEvent.popState(window);
    expect(screen.getAllByRole("link").find((link) => link.getAttribute("href") === "/settings"))
      .toHaveAttribute("aria-current", "page");
  });

  it("reports backend connectivity from the schema API result", async () => {
    let resolveSchemas: ((value: { items: []; total: number }) => void) | undefined;
    vi.mocked(api.listSchemas).mockReturnValue(
      new Promise((resolve) => { resolveSchemas = resolve; })
    );
    window.history.replaceState({}, "", "/");
    render(<RouteHarness />);

    expect(screen.getByText("后端状态：检查中")).toBeInTheDocument();

    resolveSchemas?.({ items: [], total: 0 });
    await waitFor(() => expect(screen.getByText("后端状态：已连接")).toBeInTheDocument());
  });

  it("reports backend failure when the connectivity check rejects", async () => {
    vi.mocked(api.listSchemas).mockRejectedValue(new Error("offline"));
    window.history.replaceState({}, "", "/");
    render(<RouteHarness />);

    await waitFor(() => expect(screen.getByText("后端状态：未连接")).toBeInTheDocument());
  });
});
