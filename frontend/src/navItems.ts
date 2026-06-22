import { Archive, FileInput, FileText, GitBranch, ListChecks } from "lucide-react";

import type { NavItem } from "./appTypes";

export const NAV_ITEMS: NavItem[] = [
  {
    id: "import",
    label: "Import",
    description: "Load UIR, schema, and template",
    icon: FileInput,
  },
  {
    id: "tasks",
    label: "Tasks",
    description: "Inspect conversion tasks",
    icon: ListChecks,
  },
  {
    id: "mapping",
    label: "Mapping",
    description: "Review field alignment",
    icon: GitBranch,
  },
  {
    id: "detail",
    label: "Detail",
    description: "Read canonical and reports",
    icon: FileText,
  },
  {
    id: "package",
    label: "Package",
    description: "Create and download ZIP",
    icon: Archive,
  },
];
