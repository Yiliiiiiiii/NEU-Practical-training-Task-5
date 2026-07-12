import { useRoute } from "./app/router";
import { AppShell } from "./layouts/AppShell";
import { ConversionPage } from "./pages/conversion/ConversionPage";
import { EvidencePage } from "./pages/evidence/EvidencePage";
import { ExecutionPage } from "./pages/execution/ExecutionPage";
import { OverviewPage } from "./pages/overview/OverviewPage";
import { ReviewPage } from "./pages/review/ReviewPage";
import { SchemaPacksPage } from "./pages/schemapacks/SchemaPacksPage";
import { SettingsPage } from "./pages/settings/SettingsPage";
import { TaskDetailPage } from "./pages/task-detail/TaskDetailPage";
import { TasksPage } from "./pages/tasks/TasksPage";

export default function App() {
  const route = useRoute();
  const page =
    route.name === "conversion" ? <ConversionPage /> :
    route.name === "execution" ? <ExecutionPage taskId={route.taskId} /> :
    route.name === "overview" ? <OverviewPage /> :
    route.name === "tasks" ? <TasksPage /> :
    route.name === "taskDetail" ? <TaskDetailPage taskId={route.taskId} /> :
    route.name === "review" ? <ReviewPage /> :
    route.name === "schemaPacks" ? <SchemaPacksPage /> :
    route.name === "evidence" ? <EvidencePage /> :
    route.name === "settings" ? <SettingsPage /> :
    <OverviewPage />;

  return <AppShell route={route}>{page}</AppShell>;
}
