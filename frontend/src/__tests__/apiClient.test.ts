import { describe, expect, it } from "vitest";

import { buildApiUrl, extractApiError } from "../api/client";

describe("api client helpers", () => {
  it("joins base URL and path without duplicate slashes", () => {
    expect(buildApiUrl("http://x/api/v1/", "/tasks")).toBe("http://x/api/v1/tasks");
  });

  it("extracts FastAPI detail errors", async () => {
    const response = new Response(JSON.stringify({ detail: "task not found" }), {
      status: 404,
      headers: { "content-type": "application/json" },
    });

    await expect(extractApiError(response, "加载 Task")).resolves.toContain(
      "task not found",
    );
  });
});
