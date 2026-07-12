import { describe, expect, it } from "vitest";

import { formatStatus } from "./format";
import { parseRoute } from "./router";

describe("parseRoute", () => {
  it.each([
    ["/", { name: "overview" }],
    ["/conversions/new", { name: "conversion" }],
    ["/conversions/executing/task-42", { name: "execution", taskId: "task-42" }],
    ["/tasks", { name: "tasks" }],
    ["/tasks/task-42", { name: "taskDetail", taskId: "task-42" }],
    ["/review", { name: "review" }],
    ["/schemapacks", { name: "schemaPacks" }],
    ["/evidence", { name: "evidence" }],
    ["/settings", { name: "settings" }]
  ])("parses the exact path %s", (pathname, expected) => {
    expect(parseRoute(pathname)).toEqual(expected);
  });

  it("decodes task identifiers in dynamic paths", () => {
    expect(parseRoute("/tasks/task%2F42")).toEqual({
      name: "taskDetail",
      taskId: "task/42"
    });
  });

  it.each([
    "/conversions",
    "/conversions/new/next",
    "/conversions/executing",
    "/conversions/executing/task-42/next",
    "/tasks/",
    "/tasks/task-42/next",
    "/review/next",
    "/unknown"
  ])("falls back to the overview for non-matching path %s", (pathname) => {
    expect(parseRoute(pathname)).toEqual({ name: "overview" });
  });
});

describe("formatStatus", () => {
  it.each([
    ["completed", "已完成"],
    ["verified", "已验证"],
    ["review_required", "需要复核"],
    ["failed", "失败"],
    ["running", "进行中"],
    ["pending", "待处理"],
    ["blocked", "已阻断"],
    ["unmapped", "未映射"],
    ["unverified", "未验证"]
  ])("formats %s in Chinese", (status, label) => {
    expect(formatStatus(status)).toBe(label);
  });
});
