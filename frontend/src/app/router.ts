import { useEffect, useState } from "react";

export type AppRoute =
  | { name: "overview" }
  | { name: "conversion" }
  | { name: "execution"; taskId: string }
  | { name: "tasks" }
  | { name: "taskDetail"; taskId: string }
  | { name: "review" }
  | { name: "schemaPacks" }
  | { name: "evidence" }
  | { name: "settings" };

const fixedRoutes: Record<string, AppRoute> = {
  "/": { name: "overview" },
  "/conversions/new": { name: "conversion" },
  "/tasks": { name: "tasks" },
  "/review": { name: "review" },
  "/schemapacks": { name: "schemaPacks" },
  "/evidence": { name: "evidence" },
  "/settings": { name: "settings" }
};

function decodeRouteId(value: string): string | null {
  try {
    return decodeURIComponent(value);
  } catch {
    return null;
  }
}

export function parseRoute(pathname: string): AppRoute {
  const fixedRoute = fixedRoutes[pathname];
  if (fixedRoute) {
    return fixedRoute;
  }

  const executionMatch = /^\/conversions\/executing\/([^/]+)$/.exec(pathname);
  if (executionMatch) {
    const taskId = decodeRouteId(executionMatch[1]);
    return taskId ? { name: "execution", taskId } : { name: "overview" };
  }

  const taskMatch = /^\/tasks\/([^/]+)$/.exec(pathname);
  if (taskMatch) {
    const taskId = decodeRouteId(taskMatch[1]);
    return taskId ? { name: "taskDetail", taskId } : { name: "overview" };
  }

  return { name: "overview" };
}

export function navigate(pathname: string) {
  window.history.pushState({}, "", pathname);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function useRoute(): AppRoute {
  const [route, setRoute] = useState(() => parseRoute(window.location.pathname));

  useEffect(() => {
    const updateRoute = () => setRoute(parseRoute(window.location.pathname));
    window.addEventListener("popstate", updateRoute);
    return () => window.removeEventListener("popstate", updateRoute);
  }, []);

  return route;
}
