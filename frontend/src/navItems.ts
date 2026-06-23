import { Archive, FileInput, FileText, GitBranch, ListChecks } from "lucide-react";

import type { NavItem } from "./appTypes";

export const NAV_ITEMS: NavItem[] = [
  {
    id: "import",
    label: "导入 UIR",
    description: "准备 UIR、Schema 与 Template",
    icon: FileInput,
  },
  {
    id: "tasks",
    label: "Task",
    description: "查看转换 Task",
    icon: ListChecks,
  },
  {
    id: "mapping",
    label: "Mapping",
    description: "审核字段对齐",
    icon: GitBranch,
  },
  {
    id: "detail",
    label: "详情",
    description: "查看 Canonical 与报告",
    icon: FileText,
  },
  {
    id: "package",
    label: "Package",
    description: "生成并下载 ZIP",
    icon: Archive,
  },
];
