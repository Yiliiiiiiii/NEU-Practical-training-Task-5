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
          title: "Verifier 报告不可用",
          detail: error instanceof Error ? error.message : "Package 已生成，但报告查询失败。",
        });
      }
      onSelectionChange({ ...selection, taskStatus: response.status });
      onToast?.({
        tone: "success",
        title: "Package 已验证",
        detail: response.package_id,
      });
    } catch (error) {
      onToast?.({
        tone: "danger",
        title: "Package 失败",
        detail: error instanceof Error ? error.message : "Package 生成异常。",
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
        title: "下载已开始",
        detail: download.sha256 ? `SHA-256 ${download.sha256}` : "standard_package.zip",
      });
    } catch (error) {
      onToast?.({
        tone: "danger",
        title: "下载失败",
        detail: error instanceof Error ? error.message : "ZIP 下载异常。",
      });
    } finally {
      setIsBusy(false);
    }
  }

  if (!selection.taskId) {
    return (
      <section className="document-panel">
        <div className="empty-state">
          <strong>未选择 Task。</strong>
          <span>请先打开并成功转换一个 Task，再创建标准 Package。</span>
        </div>
      </section>
    );
  }

  const readyToPackage = ["rendered", "completed"].includes(selection.taskStatus ?? "");

  return (
    <section className="document-panel package-page" aria-labelledby="package-page-title">
      <div className="document-panel__header">
        <div>
          <span className="section-label">交付校验</span>
          <h2 id="package-page-title">Package 下载</h2>
          <p>校验全部输出，生成 Manifest，并下载已验证的 ZIP artifact。</p>
        </div>
        <StatusBadge status={selection.taskStatus ?? "created"} />
      </div>

      <div className="package-action-band">
        <Archive aria-hidden="true" size={21} />
        <div>
          <strong>standard_package.zip</strong>
          <span>包含 content、chunks、reports、metadata、trace 与 SHA-256 Manifest 证据。</span>
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
          {isBusy ? "处理中..." : "生成 Package"}
        </button>
      </div>

      {!readyToPackage ? (
        <div className="inline-notice inline-notice--warning">
          请先成功转换 Task，再执行 Package。
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
            下载 ZIP
          </button>
        </>
      ) : (
        <div className="empty-state">
          <strong>本次会话尚未生成 Package。</strong>
          <span>生成 Package 前会先执行 validation 与 consistency 检查。</span>
        </div>
      )}
    </section>
  );
}
