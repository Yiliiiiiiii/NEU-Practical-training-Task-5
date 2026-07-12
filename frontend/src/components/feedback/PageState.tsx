import type { ReactNode } from "react";

export type PageStateKind = "loading" | "empty" | "error" | "offline" | "partial";

export type PageStateProps = {
  kind: PageStateKind;
  title?: string;
  detail?: ReactNode;
};

const stateLabels: Record<PageStateKind, string> = {
  loading: "正在加载",
  empty: "暂无数据",
  error: "加载失败",
  offline: "当前离线",
  partial: "部分数据不可用"
};

export function PageState({ kind, title, detail }: PageStateProps) {
  const role = kind === "error" ? "alert" : "status";

  return (
    <section
      className={`page-state page-state-${kind}`}
      role={role}
      aria-live={kind === "error" ? undefined : "polite"}
    >
      <strong>{title ?? stateLabels[kind]}</strong>
      {detail ? <p>{detail}</p> : null}
    </section>
  );
}
