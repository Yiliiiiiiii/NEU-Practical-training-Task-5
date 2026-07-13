// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { useRoute } from "../app/router";
import { AppShell } from "./AppShell";

vi.mock("../api", () => ({
  api: {
    health: vi.fn()
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
    vi.mocked(api.health).mockResolvedValue({ status: "ok" });
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

  it("uses the health endpoint and reports connectivity", async () => {
    let resolveHealth: ((value: { status: string }) => void) | undefined;
    vi.mocked(api.health).mockReturnValue(
      new Promise((resolve) => { resolveHealth = resolve; })
    );
    window.history.replaceState({}, "", "/");
    render(<RouteHarness />);

    expect(screen.getByText("后端状态：检查中")).toBeInTheDocument();

    resolveHealth?.({ status: "ok" });
    await waitFor(() => expect(screen.getByText("后端状态：已连接")).toBeInTheDocument());
    expect(api.health).toHaveBeenCalledTimes(1);
  });

  it("reports backend failure when the connectivity check rejects", async () => {
    vi.mocked(api.health).mockRejectedValue(new Error("offline"));
    window.history.replaceState({}, "", "/");
    render(<RouteHarness />);

    await waitFor(() => expect(screen.getByText("后端状态：未连接")).toBeInTheDocument());
  });

  it("retries the health check from the Chinese refresh action", async () => {
    vi.mocked(api.health)
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ status: "ok" });
    window.history.replaceState({}, "", "/");
    render(<RouteHarness />);

    await screen.findByText("后端状态：未连接");
    fireEvent.click(screen.getByRole("button", { name: "重新检查" }));

    await waitFor(() => expect(screen.getByText("后端状态：已连接")).toBeInTheDocument());
    expect(api.health).toHaveBeenCalledTimes(2);
  });

  it("ignores an older health failure after a newer StrictMode health success", async () => {
    let rejectFirst: ((reason?: unknown) => void) | undefined;
    let resolveSecond: ((value: { status: string }) => void) | undefined;
    vi.mocked(api.health)
      .mockReturnValueOnce(new Promise((_, reject) => { rejectFirst = reject; }))
      .mockReturnValueOnce(new Promise((resolve) => { resolveSecond = resolve; }));
    window.history.replaceState({}, "", "/");
    render(<StrictMode><RouteHarness /></StrictMode>);

    resolveSecond?.({ status: "ok" });
    await screen.findByText("后端状态：已连接");
    rejectFirst?.(new Error("stale offline"));

    await waitFor(() => expect(screen.getByText("后端状态：已连接")).toBeInTheDocument());
    expect(screen.queryByText("后端状态：未连接")).not.toBeInTheDocument();
  });
});
