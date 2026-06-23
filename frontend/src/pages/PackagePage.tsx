import { Archive, Download, PackageCheck } from "lucide-react";
import { useState } from "react";

import { api, downloadPackage } from "../api/client";
import type { PackageResponse, ReportResponse } from "../api/types";
import type { ToastInput, WorkbenchSelection } from "../appTypes";
import { PackageSummary } from "../components/PackageSummary";
import { StatusBadge } from "../components/StatusBadge";

interface PackagePageProps {
  selection: WorkbenchSelection;
  onSelectionChange: (selection: WorkbenchSelection) => void;
  onToast?: (toast: ToastInput) => void;
}

export function PackagePage({ selection, onSelectionChange, onToast }: PackagePageProps) {
  const [packageVersion, setPackageVersion] = useState("1.0.0");
  const [result, setResult] = useState<PackageResponse | null>(null);
  const [verifierReport, setVerifierReport] = useState<ReportResponse | null>(null);
  const [downloadSha, setDownloadSha] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  async function handlePackage() {
    if (!selection.taskId) {
      return;
    }
    setIsBusy(true);
    try {
      const response = await api.createPackage(selection.taskId, packageVersion.trim() || "1.0.0");
      setResult(response);
      try {
        setVerifierReport(await api.getPackageVerifierReport(selection.taskId));
      } catch (error) {
        setVerifierReport(null);
        onToast?.({
          tone: "warning",
          title: "Verifier report unavailable",
          detail: error instanceof Error ? error.message : "Package was built, but report lookup failed.",
        });
      }
      onSelectionChange({ ...selection, taskStatus: response.status });
      onToast?.({
        tone: "success",
        title: "Package verified",
        detail: response.package_id,
      });
    } catch (error) {
      onToast?.({
        tone: "danger",
        title: "Packaging failed",
        detail: error instanceof Error ? error.message : "Unexpected packaging failure.",
      });
    } finally {
      setIsBusy(false);
    }
  }

  async function handleDownload() {
    if (!selection.taskId) {
      return;
    }
    setIsBusy(true);
    try {
      const download = await downloadPackage(selection.taskId);
      const href = URL.createObjectURL(download.blob);
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.download = "standard_package.zip";
      anchor.click();
      URL.revokeObjectURL(href);
      setDownloadSha(download.sha256);
      onToast?.({
        tone: "success",
        title: "Download started",
        detail: download.sha256 ? `SHA-256 ${download.sha256}` : "standard_package.zip",
      });
    } catch (error) {
      onToast?.({
        tone: "danger",
        title: "Download failed",
        detail: error instanceof Error ? error.message : "Unexpected download failure.",
      });
    } finally {
      setIsBusy(false);
    }
  }

  if (!selection.taskId) {
    return (
      <section className="document-panel">
        <div className="empty-state">
          <strong>No task selected.</strong>
          <span>Open and convert a task before creating a standard package.</span>
        </div>
      </section>
    );
  }

  const readyToPackage = ["rendered", "completed"].includes(selection.taskStatus ?? "");

  return (
    <section className="document-panel package-page" aria-labelledby="package-page-title">
      <div className="document-panel__header">
        <div>
          <span className="section-label">Verified delivery</span>
          <h2 id="package-page-title">Package download</h2>
          <p>Validate all outputs, build the manifest, and download the verified ZIP artifact.</p>
        </div>
        <StatusBadge status={selection.taskStatus ?? "created"} />
      </div>

      <div className="package-action-band">
        <Archive aria-hidden="true" size={21} />
        <div>
          <strong>standard_package.zip</strong>
          <span>Content, chunks, reports, metadata, trace, and SHA-256 manifest evidence.</span>
        </div>
        <label>
          Package version
          <input
            onChange={(event) => setPackageVersion(event.target.value)}
            type="text"
            value={packageVersion}
          />
        </label>
        <button
          className="primary-button"
          disabled={isBusy || !readyToPackage}
          onClick={() => void handlePackage()}
          type="button"
        >
          <PackageCheck aria-hidden="true" size={16} />
          {isBusy ? "Working..." : "Build package"}
        </button>
      </div>

      {!readyToPackage ? (
        <div className="inline-notice inline-notice--warning">
          Convert the task successfully before packaging.
        </div>
      ) : null}

      {result ? (
        <>
          <PackageSummary
            downloadSha={downloadSha}
            result={result}
            verifierReport={verifierReport}
          />
          <button
            className="secondary-button package-proof__download"
            disabled={isBusy}
            onClick={() => void handleDownload()}
            type="button"
          >
            <Download aria-hidden="true" size={16} />
            Download ZIP
          </button>
        </>
      ) : (
        <div className="empty-state">
          <strong>No package generated in this session.</strong>
          <span>Building runs validation and consistency checks before publishing the ZIP.</span>
        </div>
      )}
    </section>
  );
}
