import { type AppRoute, useRoute } from "./app/router";
import { AppShell } from "./layouts/AppShell";
import { ConversionPage } from "./pages/conversion/ConversionPage";
import { EvidencePage } from "./pages/evidence/EvidencePage";
import { OverviewPage } from "./pages/overview/OverviewPage";
import { ReviewPage } from "./pages/review/ReviewPage";
import { SchemaPacksPage } from "./pages/schemapacks/SchemaPacksPage";
import { SettingsPage } from "./pages/settings/SettingsPage";
import { TasksPage } from "./pages/tasks/TasksPage";

type DeferredRoute = Extract<AppRoute, { name: "execution" | "taskDetail" }>;

function DeferredPage({ route }: { route: DeferredRoute }) {
  const content =
    route.name === "execution"
      ? {
          eyebrow: "转换",
          title: "执行转换",
          description: `任务 ${route.taskId} 正在等待执行视图。`,
          state: "执行状态将在此处展示。"
        }
      : {
          eyebrow: "任务",
          title: "任务详情",
          description: `任务 ${route.taskId} 的详情将在此处呈现。`,
          state: "任务详情将在后续页面中加载。"
        };

  return (
    <section className="route-placeholder" aria-labelledby="route-title">
      <p className="page-eyebrow">{content.eyebrow}</p>
      <h1 id="route-title">{content.title}</h1>
      <p className="route-placeholder-description">{content.description}</p>
      <div className="page-state page-state-empty" role="status">
        <strong>{content.state}</strong>
      </div>
    </section>
  );
}

export default function App() {
  const route = useRoute();
  const page =
    route.name === "conversion" ? <ConversionPage /> :
    route.name === "overview" ? <OverviewPage /> :
    route.name === "tasks" ? <TasksPage /> :
    route.name === "review" ? <ReviewPage /> :
    route.name === "schemaPacks" ? <SchemaPacksPage /> :
    route.name === "evidence" ? <EvidencePage /> :
    route.name === "settings" ? <SettingsPage /> :
    <DeferredPage route={route} />;

  return <AppShell route={route}>{page}</AppShell>;
}
