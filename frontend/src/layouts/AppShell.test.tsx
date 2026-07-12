// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { useRoute } from "../app/router";
import { AppShell } from "./AppShell";

function RouteHarness() {
  const route = useRoute();

  return (
    <AppShell route={route}>
      <h1>占位内容</h1>
    </AppShell>
  );
}

afterEach(cleanup);

describe("AppShell", () => {
  it("renders the seven global navigation links and identifies the current route", () => {
    window.history.replaceState({}, "", "/review");
    render(<RouteHarness />);

    expect(screen.getByRole("link", { name: "概览" }).getAttribute("href")).toBe("/");
    expect(screen.getByRole("link", { name: "新建转换" }).getAttribute("href")).toBe(
      "/conversions/new"
    );
    expect(screen.getByRole("link", { name: "任务" }).getAttribute("href")).toBe("/tasks");
    expect(screen.getByRole("link", { name: "复核" }).getAttribute("href")).toBe("/review");
    expect(screen.getByRole("link", { name: "SchemaPacks" }).getAttribute("href")).toBe(
      "/schemapacks"
    );
    expect(screen.getByRole("link", { name: "证据" }).getAttribute("href")).toBe("/evidence");
    expect(screen.getByRole("link", { name: "设置" }).getAttribute("href")).toBe("/settings");
    expect(screen.getByRole("link", { name: "复核" }).getAttribute("aria-current")).toBe(
      "page"
    );
    expect(screen.getByRole("button", { name: "收起导航" })).toBeTruthy();
  });

  it("updates navigation after link and browser history changes and can collapse the sidebar", () => {
    window.history.replaceState({}, "", "/");
    render(<RouteHarness />);

    fireEvent.click(screen.getByRole("button", { name: "收起导航" }));
    expect(screen.getByRole("button", { name: "展开导航" })).toBeTruthy();

    fireEvent.click(screen.getByRole("link", { name: "任务" }));
    expect(screen.getByRole("link", { name: "任务" }).getAttribute("aria-current")).toBe("page");

    window.history.pushState({}, "", "/settings");
    fireEvent.popState(window);
    expect(screen.getByRole("link", { name: "设置" }).getAttribute("aria-current")).toBe("page");
  });
});
