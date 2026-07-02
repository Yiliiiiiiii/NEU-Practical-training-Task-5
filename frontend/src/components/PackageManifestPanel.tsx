import { mergeManifestVerification, truncateSha } from "../evidence";
import type { PackageManifest, VerifierReport } from "../types";

export type PackageManifestPanelProps = {
  manifest: PackageManifest | null;
  verifier: VerifierReport | null;
};

export function PackageManifestPanel({ manifest, verifier }: PackageManifestPanelProps) {
  if (!manifest) {
    return <div className="empty-state">暂无 Package Manifest。</div>;
  }
  const files = mergeManifestVerification(manifest, verifier);
  return (
    <div className="evidence-panel manifest-panel">
      <div className={verifier?.passed ? "pass-line" : "fail-line"}>
        {verifier?.passed ? "Verifier 已通过" : "Verifier 不可用或未通过"}
      </div>
      <table>
        <thead>
          <tr><th>路径</th><th>大小</th><th>SHA-256</th><th>验证</th></tr>
        </thead>
        <tbody>
          {files.map((file) => (
            <tr key={file.path}>
              <td>{file.path}</td>
              <td>{file.size_bytes}</td>
              <td>
                <details>
                  <summary>{truncateSha(file.sha256)}</summary>
                  <code>{file.sha256}</code>
                </details>
              </td>
              <td>{file.verified ? "是" : "待 Review"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
