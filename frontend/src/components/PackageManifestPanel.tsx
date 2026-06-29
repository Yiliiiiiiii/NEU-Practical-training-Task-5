import { mergeManifestVerification, truncateSha } from "../evidence";
import type { PackageManifest, VerifierReport } from "../types";

export type PackageManifestPanelProps = {
  manifest: PackageManifest | null;
  verifier: VerifierReport | null;
};

export function PackageManifestPanel({ manifest, verifier }: PackageManifestPanelProps) {
  if (!manifest) {
    return <div className="empty-state">No package manifest yet.</div>;
  }
  const files = mergeManifestVerification(manifest, verifier);
  return (
    <div className="evidence-panel manifest-panel">
      <div className={verifier?.passed ? "pass-line" : "fail-line"}>
        {verifier?.passed ? "Verifier passed" : "Verifier unavailable or failed"}
      </div>
      <table>
        <thead>
          <tr><th>Path</th><th>Size</th><th>SHA-256</th><th>Verified</th></tr>
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
              <td>{file.verified ? "yes" : "review"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
