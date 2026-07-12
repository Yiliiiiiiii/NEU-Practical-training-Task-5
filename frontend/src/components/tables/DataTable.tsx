import type { ReactNode } from "react";

export type DataTableProps = {
  children: ReactNode;
  className?: string;
  label?: string;
};

export function DataTable({ children, className, label = "数据表格" }: DataTableProps) {
  return (
    <div
      className={["data-table", className].filter(Boolean).join(" ")}
      role="region"
      aria-label={label}
      tabIndex={0}
      style={{ overflowX: "auto" }}
    >
      {children}
    </div>
  );
}
