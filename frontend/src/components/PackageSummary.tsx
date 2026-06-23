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
    return "Unavailable";
  }
  const count = report.summary.verified_payloads;
  return typeof count === "number" ? String(count) : "Unavailable";
}

function getIssueCount(report: ReportResponse | null): string {
  if (!report || !Array.isArray(report.issues)) {
    return "Unavailable";
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
          <span className="section-label">Artifact evidence</span>
          <h3 id="package-summary-title">Package Summary</h3>
        </div>
        <StatusBadge status={result.status} />
      </div>

      <div className="package-proof">
        <div><span>Package ID</span><strong>{result.package_id}</strong></div>
        <div><span>ZIP path</span><strong>{result.zip_path}</strong></div>
        <div><span>SHA-256</span><code>{result.sha256 ?? "Unavailable"}</code></div>
        <div><span>Files</span><strong>{STANDARD_PACKAGE_FILES.length}</strong></div>
        <div className="package-proof__verifier">
          <span>External verifier</span>
          <strong>{verifierReport?.passed === true ? "Verifier passed" : "Verifier pending"}</strong>
          <small>{verifiedPayloads} payloads, {issueCount} issues</small>
        </div>
        {downloadSha ? <div><span>Download header</span><code>{downloadSha}</code></div> : null}
      </div>

      <div className="manifest-file-list" aria-label="Standard package files">
        {STANDARD_PACKAGE_FILES.map((file) => (
          <span className="file-chip" key={file}>{file}</span>
        ))}
      </div>
    </section>
  );
}
