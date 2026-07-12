import { AppShell } from "./layouts/AppShell";
import { useRoute, type AppRoute } from "./app/router";
import { ConversionPage } from "./pages/conversion/ConversionPage";

type PlaceholderContent = {
  eyebrow: string;
  title: string;
  description: string;
  state: string;
};

function placeholderFor(route: AppRoute): PlaceholderContent {
  switch (route.name) {
    case "conversion":
      return {
        eyebrow: "转换",
        title: "新建转换",
        description: "选择 Schema 后创建新的转换任务。",
        state: "转换流程将在此处继续。"
      };
    case "execution":
      return {
        eyebrow: "转换",
        title: "执行转换",
        description: `任务 ${route.taskId} 正在等待执行视图。`,
        state: "执行状态将在此处展示。"
      };
    case "tasks":
      return {
        eyebrow: "任务",
        title: "任务",
        description: "查看和管理已创建的转换任务。",
        state: "当前没有可显示的任务。"
      };
    case "taskDetail":
      return {
        eyebrow: "任务",
        title: "任务详情",
        description: `任务 ${route.taskId} 的详情将在此处呈现。`,
        state: "任务详情将在后续页面中加载。"
      };
    case "review":
      return {
        eyebrow: "复核",
        title: "复核",
        description: "集中处理需要人工确认的转换结果。",
        state: "当前没有待复核内容。"
      };
    case "schemaPacks":
      return {
        eyebrow: "SchemaPacks",
        title: "SchemaPacks",
        description: "管理 Schema、模板和 Package 版本。",
        state: "SchemaPacks 将在此处列出。"
      };
    case "evidence":
      return {
        eyebrow: "证据",
        title: "证据",
        description: "追踪转换过程中的来源、映射和校验信息。",
        state: "证据记录将在此处显示。"
      };
    case "settings":
      return {
        eyebrow: "设置",
        title: "设置",
        description: "配置本地工作环境与转换偏好。",
        state: "设置项将在此处提供。"
      };
    case "overview":
    default:
      return {
        eyebrow: "概览",
        title: "工作概览",
        description: "从这里进入转换、任务、复核与证据工作流。",
        state: "当前本地会话没有进行中的转换。"
      };
  }
}

function PlaceholderPage({ content }: { content: PlaceholderContent }) {
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

  return (
    <AppShell route={route}>
      {route.name === "conversion" ? <ConversionPage /> : <PlaceholderPage content={placeholderFor(route)} />}
    </AppShell>
  );
}
