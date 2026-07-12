import {
  Boxes,
  ClipboardCheck,
  FileSearch,
  LayoutDashboard,
  ListTodo,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  SquarePlus,
  type LucideIcon
} from "lucide-react";
import { useState, type MouseEvent, type ReactNode } from "react";

import { navigate, type AppRoute } from "../app/router";

type NavigationItem = {
  label: string;
  href: string;
  icon: LucideIcon;
  isActive: (route: AppRoute) => boolean;
};

type AppShellProps = {
  route: AppRoute;
  children: ReactNode;
};

const navigationItems: NavigationItem[] = [
  {
    label: "概览",
    href: "/",
    icon: LayoutDashboard,
    isActive: (route) => route.name === "overview"
  },
  {
    label: "新建转换",
    href: "/conversions/new",
    icon: SquarePlus,
    isActive: (route) => route.name === "conversion" || route.name === "execution"
  },
  {
    label: "任务",
    href: "/tasks",
    icon: ListTodo,
    isActive: (route) => route.name === "tasks" || route.name === "taskDetail"
  },
  {
    label: "复核",
    href: "/review",
    icon: ClipboardCheck,
    isActive: (route) => route.name === "review"
  },
  {
    label: "SchemaPacks",
    href: "/schemapacks",
    icon: Boxes,
    isActive: (route) => route.name === "schemaPacks"
  },
  {
    label: "证据",
    href: "/evidence",
    icon: FileSearch,
    isActive: (route) => route.name === "evidence"
  },
  {
    label: "设置",
    href: "/settings",
    icon: Settings,
    isActive: (route) => route.name === "settings"
  }
];

function handleNavigation(event: MouseEvent<HTMLAnchorElement>, href: string) {
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return;
  }

  event.preventDefault();
  navigate(href);
}

export function AppShell({ route, children }: AppShellProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const ToggleIcon = isCollapsed ? PanelLeftOpen : PanelLeftClose;
  const toggleLabel = isCollapsed ? "展开导航" : "收起导航";

  return (
    <div className={`application-shell${isCollapsed ? " is-navigation-collapsed" : ""}`}>
      <aside className="application-sidebar" aria-label="主导航">
        <div className="application-sidebar-header">
          <a
            className="application-mark"
            href="/"
            aria-label="SchemaPack Agent 概览"
            onClick={(event) => handleNavigation(event, "/")}
          >
            <Boxes aria-hidden="true" size={20} strokeWidth={1.75} />
          </a>
          <span className="application-sidebar-name">工作台</span>
          <button
            className="navigation-toggle"
            type="button"
            aria-label={toggleLabel}
            title={toggleLabel}
            onClick={() => setIsCollapsed((value) => !value)}
          >
            <ToggleIcon aria-hidden="true" size={18} />
          </button>
        </div>

        <nav className="application-navigation" aria-label="功能导航">
          {navigationItems.map(({ href, icon: Icon, isActive, label }) => {
            const active = isActive(route);

            return (
              <a
                key={href}
                className={`application-navigation-link${active ? " is-active" : ""}`}
                href={href}
                aria-current={active ? "page" : undefined}
                aria-label={label}
                onClick={(event) => handleNavigation(event, href)}
              >
                <Icon aria-hidden="true" size={18} strokeWidth={1.8} />
                <span className="application-navigation-label">{label}</span>
              </a>
            );
          })}
        </nav>
      </aside>

      <div className="application-frame">
        <header className="application-topbar">
          <div className="application-identity">
            <strong>SchemaPack Agent</strong>
            <span>本地环境</span>
          </div>
          <div className="application-session" aria-label="应用状态">
            <span className="backend-status"><i aria-hidden="true" />后端状态：未连接</span>
            <span>本地会话</span>
          </div>
        </header>
        <main className="application-content">{children}</main>
      </div>
    </div>
  );
}
