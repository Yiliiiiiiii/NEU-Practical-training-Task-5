import { PageState } from "../../components/feedback/PageState";
import { DataTable } from "../../components/tables/DataTable";
import type { PackageManifest, PackageMetadata, VerifierReport } from "../../types";

export function PackageTab({
  taskId,
  manifest,
  verifier,
  packageMetadata,
  loading,
  packageDownloadUrl
}: {
  taskId: string;
  manifest: PackageManifest | null;
  verifier: VerifierReport | null;
  packageMetadata: PackageMetadata | null;
  loading: boolean;
  packageDownloadUrl: (taskId: string) => string;
}) {
  if (loading) return <PageState kind="loading" title="正在读取 Package 报告" />;

  const passed = verifier?.passed === true;
  const downloadReason = "当前没有已通过验证器校验的 Package，因此不能下载。";
  return (
    <section className="task-detail-package-tab" aria-labelledby="package-report-title">
      <h2 id="package-report-title">Package 可信状态</h2>
      {verifier ? (
        <p className={passed ? "task-detail-package-trust task-detail-package-trust-passed" : "task-detail-package-trust task-detail-package-trust-warning"}>
          验证器：{passed ? "已通过" : "未通过"}
        </p>
      ) : <PageState kind="empty" title="验证器报告尚未生成" />}
      <dl>
        <div><dt>产物状态</dt><dd>{packageMetadata?.status ?? "—"}</dd></div>
        <div><dt>Package SHA-256</dt><dd>{packageMetadata?.sha256 ?? "—"}</dd></div>
        <div><dt>产物路径</dt><dd>{packageMetadata?.zip_path ?? "—"}</dd></div>
      </dl>
      {passed ? (
        <a className="task-detail-package-download" href={packageDownloadUrl(taskId)}>下载已验证 Package</a>
      ) : (
        <>
          <button type="button" disabled aria-describedby="package-download-reason">下载已验证 Package</button>
          <p id="package-download-reason" className="task-detail-package-warning">{downloadReason}</p>
        </>
      )}
      {manifest ? (
        <DataTable className="task-detail-package-table" label="Package Manifest 文件表">
          <table>
            <thead><tr><th>文件</th><th>用途</th><th>大小</th><th>SHA-256</th></tr></thead>
            <tbody>
              {manifest.files.map((file) => <tr key={file.path}><td>{file.path}</td><td>{file.role ?? "—"}</td><td>{file.size_bytes}</td><td>{file.sha256}</td></tr>)}
            </tbody>
          </table>
        </DataTable>
      ) : <PageState kind="empty" title="Manifest 尚未生成" />}
    </section>
  );
}
