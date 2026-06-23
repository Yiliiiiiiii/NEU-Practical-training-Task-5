import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ToastRegion } from "../components/ToastRegion";

describe("ToastRegion", () => {
  it("lets users dismiss a status message", () => {
    const onDismiss = vi.fn();
    render(
      <ToastRegion
        messages={[{ id: "toast-1", tone: "success", title: "Task 已创建" }]}
        onDismiss={onDismiss}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "关闭 Task 已创建" }));
    expect(onDismiss).toHaveBeenCalledWith("toast-1");
  });
});
