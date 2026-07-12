function localSessionState() {
  try {
    window.sessionStorage.getItem("schemapack-agent-session-check");
    return "浏览器会话存储可用";
  } catch {
    return "浏览器会话存储不可用";
  }
}

export function SettingsPage() {
  const apiBase = import.meta.env.VITE_API_BASE || "未配置（使用同源 /api）";

  return (
    <section className="route-placeholder operations-page settings-page" aria-labelledby="settings-title">
      <p className="page-eyebrow">设置</p>
      <h1 id="settings-title">运行环境</h1>
      <p className="route-placeholder-description">此页仅展示当前浏览器构建可读取的连接与会话信息。</p>
      <section className="operations-section settings-read-only" aria-labelledby="settings-readonly-title">
        <h2 id="settings-readonly-title">只读配置</h2>
        <dl>
          <div><dt>API 基址</dt><dd><code>{apiBase}</code></dd></div>
          <div><dt>环境</dt><dd>{import.meta.env.MODE}</dd></div>
          <div><dt>本地会话</dt><dd>{localSessionState()}</dd></div>
        </dl>
      </section>
      <p>后端连接由部署环境决定，本页不提供模拟或可编辑的后端控制项。</p>
    </section>
  );
}
