import type { LucideIcon } from "lucide-react";

export type ViewId = "import" | "tasks" | "mapping" | "detail" | "package";

export interface NavItem {
  id: ViewId;
  label: string;
  description: string;
  icon: LucideIcon;
}

export type StageState = "pending" | "ready" | "blocked" | "running" | "done";

export interface WorkflowStage {
  label: string;
  detail: string;
  state: StageState;
}

export interface ToastMessage {
  id: string;
  tone: "info" | "success" | "warning" | "danger";
  title: string;
  detail?: string;
}

export interface WorkbenchSelection {
  docId: string | null;
  schemaId: string | null;
  templateId: string | null;
  taskId: string | null;
}

export type ToastInput = Omit<ToastMessage, "id">;
