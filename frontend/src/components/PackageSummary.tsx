import type { JsonValue, PackageResponse, ReportResponse } from "../api/types";
import { StatusBadge } from "./StatusBadge";

interface PackageSummaryProps {
  result: PackageResponse;
  verifierReport: ReportResponse | null;
  downloadSha: string | null;
}

const STANDARD_PACKAGE_FILES = [
  "manifest.json",
  "metadata.json",
  "config_snapshot.json",
  "content.json",
  "content.md",
  "chunks.json",
  "mapping_report.json",
  "validation_report.json",
  "consistency_report.json",
  "trace.json",
];

function isRecord(value: JsonValue | undefined): value is Record<string, JsonValue> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function getVerifiedPayloadCount(report: ReportResponse | null): string {
  if (!report || !isRecord(report.summary)) {
    return "不可用";
  }
  const count = report.summary.verified_payloads;
  return typeof count === "number" ? String(count) : "不可用";
}

function getIssueCount(report: ReportResponse | null): string {
  if (!report || !Array.isArray(report.issues)) {
    return "不可用";
  }
  return String(report.issues.length);
}

export function PackageSummary({ result, verifierReport, downloadSha }: PackageSummaryProps) {
  const verifiedPayloads = getVerifiedPayloadCount(verifierReport);
  const issueCount = getIssueCount(verifierReport);

  return (
    <section className="package-summary" aria-labelledby="package-summary-title">
      <div className="package-summary__header">
        <div>
          <span className="section-label">Artifact 证据</span>
          <h3 id="package-summary-title">Package 摘要</h3>
        </div>
        <StatusBadge status={result.status} />
      </div>

      <div className="package-proof">
        <div><span>Package ID</span><strong>{result.package_id}</strong></div>
        <div><span>ZIP 路径</span><strong>{result.zip_path}</strong></div>
        <div><span>SHA-256</span><code>{result.sha256 ?? "不可用"}</code></div>
        <div><span>文件数</span><strong>{STANDARD_PACKAGE_FILES.length}</strong></div>
        <div className="package-proof__verifier">
          <span>外部 verifier</span>
          <strong>{verifierReport?.passed === true ? "Verifier 通过" : "Verifier 待执行"}</strong>
          <small>{verifiedPayloads} 个 payload，{issueCount} 个 issue</small>
        </div>
        {downloadSha ? <div><span>下载响应头</span><code>{downloadSha}</code></div> : null}
      </div>

      <div className="manifest-file-list" aria-label="标准 Package 文件">
        {STANDARD_PACKAGE_FILES.map((file) => (
          <span className="file-chip" key={file}>{file}</span>
        ))}
      </div>
    </section>
  );
}
